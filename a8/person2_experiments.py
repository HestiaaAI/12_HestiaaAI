"""Measured Person 2 retrieval runs; generation is an explicit shared-runner adapter."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import importlib.metadata
import hashlib
import math
import csv
import json
import platform
from pathlib import Path
import subprocess
from time import perf_counter

from a8.corpus import STRATEGIES, load_chunks, load_queries, load_paragraphs, word_count
from a8.retrieval import (build_index, fingerprint, load_encoder, save_index, search,
                          score_retrieval, synchronize, token_lengths)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def read_rows(path):
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []
    keys = [r['row_id'] for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f'Duplicate row IDs in {path}')
    return rows


def environment():
    packages = {}
    for name in ['numpy', 'torch', 'sentence-transformers', 'transformers', 'huggingface-hub']:
        try: packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: packages[name] = None
    try: commit = subprocess.check_output(['git','rev-parse','HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError): commit = None
    import torch
    return {'torch_threads': torch.get_num_threads(), 'python': platform.python_version(), 'platform': platform.platform(),
            'machine': platform.machine(), 'packages': packages, 'git_commit': commit}


def run_retrieval_experiments(output_dir, encoder, top_k=3, repetitions=10):
    """15 full matrix rows plus 10 scaling rows. Reuse the full/hybrid index.

    A row's initial request is measured once; scaling also saves interleaved
    warmed retrieval samples. No answer key is passed to the encoder.
    """
    if repetitions < 1 or top_k < 1:
        raise ValueError('repetitions and top_k must be positive')
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = load_queries()
    chunk_sets = {(ds, strategy): load_chunks(strategy, ds)
                  for ds in ('small','full') for strategy in STRATEGIES}
    config = {'model': encoder.a8_metadata, 'top_k': top_k, 'scaling_strategy': 'hybrid',
              'repetitions': repetitions, 'queries_sha256': fingerprint(queries),
              'chunks_sha256': {f'{ds}/{s}': fingerprint([asdict(c) for c in cs])
                                for (ds,s),cs in chunk_sets.items()},
              'environment': environment(),
              'source_sha256': {name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                                for name in ('corpus.py','retrieval.py','person2_experiments.py')},
              'warmup': 'one query per index before measured requests'}
    config_hash = fingerprint(config)
    manifest_path = output_dir/'run_manifest.json'
    if manifest_path.exists():
        if json.loads(manifest_path.read_text())['config_sha256'] != config_hash:
            raise ValueError('Run configuration changed; choose a new output directory')
    else:
        write_json(manifest_path, {'created_utc':datetime.now(timezone.utc).isoformat(),
                                  'config_sha256':config_hash, **config})
    raw = output_dir/'retrieval.jsonl'
    rows = read_rows(raw)
    if any(r['config_sha256'] != config_hash for r in rows):
        raise ValueError('Mixed configurations in saved results')
    existing = {r['row_id'] for r in rows}
    indexes = {}
    index_stats = {}
    for dataset,strategy in [('full',s) for s in STRATEGIES] + [('small','hybrid')]:
        cs = chunk_sets[dataset,strategy]
        synchronize(encoder)
        start = perf_counter()
        index = build_index(cs, encoder, encoder.a8_metadata)
        synchronize(encoder)
        elapsed = (perf_counter()-start)*1000
        indexes[dataset,strategy] = index
        save_index(index, output_dir/'indexes'/f'{dataset}-{strategy}')
        lengths = token_lengths([c.text for c in cs],encoder)
        index_stats[f'{dataset}/{strategy}'] = {
            'build_ms':elapsed, 'chunk_count':len(cs), 'vector_bytes':int(index.vectors.nbytes),
            'max_chunk_tokens':max(lengths) if lengths else None,
            'embedding_context_limit':getattr(encoder,'max_seq_length',None),
            'paragraph_count':len(load_paragraphs(dataset)),
            'word_count':sum(word_count(p.text) for p in load_paragraphs(dataset))}
        search(index, queries[0]['query'],encoder,top_k)  # Warm-up excluded.
    # Keep original build measurements on resume rather than silently overwriting them.
    if not (output_dir/'index_stats.json').exists():
        write_json(output_dir/'index_stats.json',index_stats)
    jobs = [('matrix','full',s,q) for s in STRATEGIES for q in queries]
    jobs += [('scaling',ds,'hybrid',q) for ds in ('small','full') for q in queries]
    for experiment,dataset,strategy,q in jobs:
        row_id = f"{experiment}/{dataset}/{strategy}/{q['id']}"
        if row_id in existing: continue
        timings = {}
        start = perf_counter()
        hits = search(indexes[dataset,strategy],q['query'],encoder,top_k,timings)
        retrieval_ms = (perf_counter()-start)*1000
        row = {'row_id':row_id,'config_sha256':config_hash,'experiment':experiment,
               'dataset':dataset,'embedding_model':encoder.a8_metadata['model_id'],
               'model_revision':encoder.a8_metadata['revision'],
               'embedding_dimension':encoder.a8_metadata['dimension'],
               'strategy':strategy,'top_k':top_k,'query_id':q['id'],'query':q['query'],
               'retrieved_chunks':hits, **score_retrieval(hits,q), **timings,
               'retrieval_ms':retrieval_ms,'generation_ms':None,'end_to_end_ms':None,
               'retrieved_context_quality':None,'answer_quality':None,'answer':None,
               'notes':'Retrieval measured; shared generator and human quality review pending.',
               'status':'retrieval_only'}
        with raw.open('a',encoding='utf-8') as f:
            f.write(json.dumps(row,ensure_ascii=False)+'\n')
        rows.append(row)
    expected = {f'{e}/{ds}/{s}/{q["id"]}' for e,ds,s,q in jobs}
    if {r['row_id'] for r in rows} != expected:
        raise ValueError('Saved run contains missing or unexpected query keys')
    samples_path = output_dir/'scaling_latency_samples.json'
    if not samples_path.exists():
        samples=[]
        for rep in range(repetitions):
            for q in queries:
                # Alternate order to reduce systematic first-dataset timing bias.
                for ds in (('small','full') if rep%2==0 else ('full','small')):
                    timings={}
                    start=perf_counter()
                    search(indexes[ds,'hybrid'],q['query'],encoder,top_k,timings)
                    samples.append({'repeat':rep,'dataset':ds,'query_id':q['id'],
                                    'retrieval_ms':(perf_counter()-start)*1000,**timings})
        write_json(samples_path,samples)
    export_tables(output_dir, rows)
    return rows


def attach_generation(output_dir, generate_answer, generator_manifest):
    """Call a team-supplied function with only query and ranked contexts.

    Callable returns answer, exact rendered prompt, generation_ms and explicit
    context_truncated=False. Subjective quality stays pending for shared review.
    New output preserves raw retrieval evidence; failed generation is recorded.
    """
    output_dir=Path(output_dir)
    original=read_rows(output_dir/'retrieval.jsonl')
    path=output_dir/'generation.jsonl'
    settings=output_dir/'generator_manifest.json'
    if settings.exists() and json.loads(settings.read_text())!=generator_manifest:
        raise ValueError('Generator changed; choose a separate run directory')
    write_json(settings,generator_manifest)
    rows=read_rows(path)
    existing={r['row_id'] for r in rows}
    if any(r['config_sha256'] != original[0]['config_sha256'] for r in rows):
        raise ValueError('Generation results do not match retrieval run')
    for row in original:
        if row['row_id'] in existing: continue
        result=dict(row)
        try:
            generated=generate_answer(row['query'],row['retrieved_chunks'])
            if generated.get('context_truncated') is not False:
                raise ValueError('Generator must confirm context_truncated=False')
            if not generated.get('answer') or not generated.get('prompt'):
                raise ValueError('Generator must return answer and rendered prompt')
            elapsed=generated['generation_ms']
            if not isinstance(elapsed,(float,int)) or not math.isfinite(elapsed) or elapsed<0:
                raise ValueError('generation_ms must be a nonnegative measurement')
            result.update(answer=generated['answer'],prompt=generated['prompt'],
                          generation_ms=elapsed,context_truncated=False,
                          # These stages may run at different times; do not mislabel sum as observed E2E.
                          stage_latency_sum_ms=row['retrieval_ms']+elapsed,
                          status='generation_complete_review_pending',
                          notes='Actual answer saved; shared rubric review pending. E2E requires a joint run.')
        except Exception as error:
            result.update(status='generation_error',error=f'{type(error).__name__}: {error}')
        with path.open('a',encoding='utf-8') as f:
            f.write(json.dumps(result,ensure_ascii=False)+'\n')
        rows.append(result)
    export_tables(output_dir, rows, prefix='generation')
    return rows


def export_tables(output_dir, rows, prefix='retrieval'):
    fields=['embedding_model','strategy','query_id','query','retrieved_context_quality',
            'answer_quality','retrieval_ms','generation_ms','end_to_end_ms','notes','status',
            'dataset','source_recall_at_k','source_reciprocal_rank','evidence_quote_coverage','answer']
    for experiment in ('matrix','scaling'):
        with (Path(output_dir)/f'{prefix}_{experiment}.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
            writer.writeheader()
            writer.writerows(r for r in rows if r['experiment']==experiment)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--device',default='cpu')
    parser.add_argument('--top-k',type=int,default=3)
    parser.add_argument('--repetitions',type=int,default=10)
    parser.add_argument('--revision')
    args=parser.parse_args()
    encoder=load_encoder('small',device=args.device,revision=args.revision)
    rows=run_retrieval_experiments(args.output_dir,encoder,args.top_k,args.repetitions)
    print(f'Saved {len(rows)} retrieval rows to {args.output_dir}; generation/review pending.')


if __name__=='__main__': main()
