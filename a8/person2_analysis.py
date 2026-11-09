"""Validate and export Person 2's completed RAG evidence and reviewed results."""
import argparse
from collections import Counter
import csv
from dataclasses import asdict
import json
import math
from pathlib import Path
from statistics import mean, median

from a8.corpus import STRATEGIES, load_queries, load_chunks
from a8.generation import MODEL, REVISION, MAX_NEW_TOKENS, SYSTEM, messages
from a8.person3_experiments import REVISIONS
from a8.person2_experiments import read_rows
from a8.person3_analysis import export
from a8.retrieval import score_retrieval, MODELS, fingerprint

DEFAULT = Path(__file__).resolve().parent/'results/person2/completed-2026-11-09'
CONTROLS = ('encoder','generator','revision','system','decoding','max_new_tokens','top_k',
            'generator_code','environment','query_digest')


def evaluation_table(directory=DEFAULT):
    directory=Path(directory)
    queries={q['id']:q for q in load_queries()}
    with (directory/'reviews.csv').open(encoding='utf-8') as f:
        records=list(csv.DictReader(f))
    reviews={(r['experiment'],r['row_id']):r for r in records}
    if len(reviews)!=len(records):
        raise ValueError('Duplicate reviews')
    manifests={e:json.loads((directory/e/'manifest.json').read_text()) for e in ('matrix','scaling')}
    if any(manifests['matrix'].get(k)!=manifests['scaling'].get(k) for k in CONTROLS):
        raise ValueError('Matrix and scaling controls differ')
    if any(k not in manifests['matrix'] for k in CONTROLS):
        raise ValueError('Missing experiment controls')
    frozen={'generator':MODEL,'revision':REVISION,'system':SYSTEM,
            'decoding':'greedy, 1 beam, float32 CPU','max_new_tokens':MAX_NEW_TOKENS,'top_k':3,
            'query_digest':fingerprint(load_queries()),
            'generator_code':fingerprint((Path(__file__).parent/'generation.py').read_text()),
            'encoder':{**MODELS['small'],'revision':REVISIONS['small'],
                       'device':'cpu','normalization':'l2','dtype':'float32'}}
    if any(manifests['matrix'].get(k)!=v for k,v in frozen.items()):
        raise ValueError('Manifest differs from frozen shared contract')
    results=[]
    for experiment in ('matrix','scaling'):
        rows=read_rows(directory/experiment/'rows.jsonl')
        datasets=('full',) if experiment=='matrix' else ('small','full')
        strategies=STRATEGIES if experiment=='matrix' else ('hybrid',)
        jobs={(ds,s):load_chunks(s,ds) for ds in datasets for s in strategies}
        if manifests[experiment].get('corpus_digest')!=fingerprint([[asdict(c) for c in cs] for cs in jobs.values()]):
            raise ValueError('Corpus changed since inference')
        expected={f'small/{ds}/{s}/{q}' for ds in datasets for s in strategies for q in queries}
        if {r['row_id'] for r in rows}!=expected:
            raise ValueError(f'Incomplete or unexpected {experiment} rows')
        for row in rows:
            key=experiment,row['row_id']
            if key not in reviews: raise ValueError(f'Missing review: {key}')
            review=reviews[key]
            if review['evidence_sha256']!=fingerprint(row):
                raise ValueError(f'Response/context changed; review again: {key}')
            q=queries[row['query_id']]
            if (row['query']!=q['query'] or row['row_id']!=f"small/{row['dataset']}/{row['strategy']}/{q['id']}" or
                    row['generator']!=manifests[experiment]['generator'] or
                    row['embedding_model']!=MODELS['small']['model_id'] or row['embedding_dimension']!=384 or
                    row.get('context_truncated') is not False):
                raise ValueError(f'Invalid request or truncated context: {key}')
            hits=row['retrieved_chunks']
            if len(hits)!=3 or [h['rank'] for h in hits]!=[1,2,3]:
                raise ValueError(f'Expected three ranked chunks: {key}')
            corpus={c.id:c for c in jobs[row['dataset'],row['strategy']]}
            for hit in hits:
                chunk=corpus.get(hit['chunk_id'])
                if (chunk is None or hit['text']!=chunk.text or
                        hit['paragraph_ids']!=list(chunk.paragraph_ids) or
                        hit.get('document')!=chunk.document or hit.get('section')!=chunk.section):
                    raise ValueError(f'Hit does not match frozen corpus: {key}')
            # Default no-tools ChatML rendering of the frozen Qwen2 tokenizer.
            # Verify this renderer against actual shared-run prompts, not an answer key.
            expected_prompt=''.join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
                                    for m in messages(row['query'],hits))+'<|im_start|>assistant\n'
            if row['prompt']!=expected_prompt:
                raise ValueError(f'Prompt differs from shared contract: {key}')
            metrics=score_retrieval(hits,q)
            if any(abs(metrics[k]-row[k])>1e-7 for k in ('evidence_quote_coverage','source_recall_at_k','source_reciprocal_rank')):
                raise ValueError(f'Retrieval metrics do not match saved text: {key}')
            facts=[int(x) for x in review['matched_facts'].split()]
            relevant=[int(x) for x in review['relevant_ranks'].split()]
            deductions=int(review['unsupported_count'])
            if (len(facts)!=len(set(facts)) or any(n<1 or n>len(q['required_facts']) for n in facts) or
                    deductions<0 or len(relevant)!=len(set(relevant)) or any(n not in (1,2,3) for n in relevant) or
                    not review['notes'].strip()):
                raise ValueError(f'Invalid review: {key}')
            for name in ('retrieval_ms','generation_ms','end_to_end_ms'):
                if not isinstance(row[name],(int,float)) or not math.isfinite(row[name]) or row[name]<0:
                    raise ValueError(f'Invalid latency: {key}')
            if row['end_to_end_ms']<row['retrieval_ms']+row['generation_ms']-0.01:
                raise ValueError(f'E2E latency shorter than measured stages: {key}')
            results.append(dict(experiment=experiment,row_id=row['row_id'],dataset=row['dataset'],
                embedding_model=row['embedding_model'],dimension=row['embedding_dimension'],generator=row['generator'],
                strategy=row['strategy'],query_id=q['id'],query=q['query'],
                retrieved_context_quality=round(100*metrics['evidence_quote_coverage'],2),
                answer_quality=round(100*max(0,len(facts)-deductions)/len(q['required_facts']),2),
                source_recall_at_k=metrics['source_recall_at_k'],source_reciprocal_rank=metrics['source_reciprocal_rank'],
                irrelevant_chunk_fraction=(3-len(relevant))/3,
                retrieval_ms=row['retrieval_ms'],generation_ms=row['generation_ms'],end_to_end_ms=row['end_to_end_ms'],
                reached_token_cap=row['reached_token_cap'],answer=row['answer'],notes=review['notes'],
                review_method='AI-assisted; student signoff not recorded',
                retrieved_chunks=json.dumps(hits,ensure_ascii=False)))
    if Counter(reviews.keys())!=Counter((r['experiment'],r['row_id']) for r in results):
        raise ValueError('Extra or missing reviews')
    return results


def export_results(directory=DEFAULT):
    directory=Path(directory)
    rows=evaluation_table(directory)
    for experiment in ('matrix','scaling'):
        export([r for r in rows if r['experiment']==experiment],directory/f'{experiment}_evaluation.csv')
    summaries=[]
    for ds in ('small','full'):
        part=[r for r in rows if r['experiment']=='scaling' and r['dataset']==ds]
        summaries.append(dict(dataset=ds,queries=len(part),mean_context_quality=mean(r['retrieved_context_quality'] for r in part),
            mean_answer_quality=mean(r['answer_quality'] for r in part),
            mean_irrelevant_chunk_fraction=mean(r['irrelevant_chunk_fraction'] for r in part),
            median_retrieval_ms=median(r['retrieval_ms'] for r in part),
            median_generation_ms=median(r['generation_ms'] for r in part),
            median_end_to_end_ms=median(r['end_to_end_ms'] for r in part)))
    export(summaries,directory/'scaling_summary.csv')
    pairs=[]
    for q in load_queries():
        pair={r['dataset']:r for r in rows if r['experiment']=='scaling' and r['query_id']==q['id']}
        pairs.append(dict(query_id=q['id'],small_answer_quality=pair['small']['answer_quality'],
            full_answer_quality=pair['full']['answer_quality'],
            answer_quality_delta=pair['full']['answer_quality']-pair['small']['answer_quality'],
            small_noise_fraction=pair['small']['irrelevant_chunk_fraction'],
            full_noise_fraction=pair['full']['irrelevant_chunk_fraction'],
            small_end_to_end_ms=pair['small']['end_to_end_ms'],full_end_to_end_ms=pair['full']['end_to_end_ms']))
    export(pairs,directory/'scaling_pairs.csv')
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,default=DEFAULT)
    args=parser.parse_args()
    print(f'Validated and exported {len(export_results(args.run_dir))} reviewed RAG rows.')
