"""Completion checks must reject altered outputs and mismatched scaling controls."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import asdict
from a8.corpus import STRATEGIES, load_queries, load_chunks
from a8.generation import MODEL, REVISION, MAX_NEW_TOKENS, SYSTEM, messages
from a8.person3_experiments import REVISIONS
from a8.retrieval import MODELS, fingerprint, score_retrieval
from a8.person2_analysis import evaluation_table


def fixture(directory):
    reviews=[]
    for experiment in ('matrix','scaling'):
        path=directory/experiment
        path.mkdir()
        manifest={'generator':MODEL,'revision':REVISION,
                  'encoder':{**MODELS['small'],'revision':REVISIONS['small'],'device':'cpu','normalization':'l2','dtype':'float32'},
                  'system':SYSTEM,'decoding':'greedy, 1 beam, float32 CPU','max_new_tokens':MAX_NEW_TOKENS,'top_k':3,
                  'query_digest':fingerprint(load_queries()),
                  'corpus_digest':fingerprint([[asdict(c) for c in load_chunks(s,ds)] for ds in (('full',) if experiment=='matrix' else ('small','full')) for s in (STRATEGIES if experiment=='matrix' else ('hybrid',))]),
                  'generator_code':fingerprint(Path('a8/generation.py').read_text()),'environment':{'torch_threads':4}}
        (path/'manifest.json').write_text(json.dumps(manifest))
        rows=[]
        for ds in (('full',) if experiment=='matrix' else ('small','full')):
            for strategy in (STRATEGIES if experiment=='matrix' else ('hybrid',)):
                for q in load_queries():
                    chunks=load_chunks(strategy,ds)
                    support=[c for c in chunks if set(c.paragraph_ids)&set(q['supporting_paragraph_ids'])]
                    chosen=(support+[c for c in chunks if c not in support])[:3]
                    hits=[dict(rank=i,chunk_id=c.id,document=c.document,section=c.section,text=c.text,
                               paragraph_ids=list(c.paragraph_ids),score=.5) for i,c in enumerate(chosen,1)]
                    prompt=''.join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in messages(q['query'],hits))+'<|im_start|>assistant\n'
                    row=dict(row_id=f"small/{ds}/{strategy}/{q['id']}",dataset=ds,strategy=strategy,
                             query_id=q['id'],query=q['query'],answer=q['expected_answer'],retrieved_chunks=hits,
                             embedding_model=MODELS['small']['model_id'],embedding_dimension=384,generator=MODEL,prompt=prompt,
                             **score_retrieval(hits,q),
                             retrieval_ms=1.,generation_ms=2.,end_to_end_ms=3.1,context_truncated=False,
                             reached_token_cap=False,input_tokens=100,output_tokens=25)
                    rows.append(row)
                    reviews.append(dict(experiment=experiment,row_id=row['row_id'],evidence_sha256=fingerprint(row),
                                        matched_facts=' '.join(str(i) for i in range(1,len(q['required_facts'])+1)),
                                        unsupported_count='0',relevant_ranks='1',notes='Test review rationale'))
        (path/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    with (directory/'reviews.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(reviews[0]));w.writeheader();w.writerows(reviews)


class CompletionTests(unittest.TestCase):
    def test_complete_tables_use_shared_fact_rubric_and_noise(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);fixture(p)
            rows=evaluation_table(p)
            self.assertEqual(len(rows),25)
            self.assertEqual(sum(r['experiment']=='matrix' for r in rows),15)
            self.assertTrue(all(r['answer_quality']==100. for r in rows))
            self.assertTrue(all(abs(r['irrelevant_chunk_fraction']-2/3)<1e-9 for r in rows))
            self.assertTrue(all(r['retrieved_context_quality']==100. for r in rows))

    def test_changed_response_duplicate_review_and_scaling_controls_rejected(self):
        for condition in ['answer','duplicate','generator','prompt','embedding','frozen_contract','prompt_rehashed','scaling_query_digest']:
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as d:
                p=Path(d);fixture(p)
                if condition in ('answer','prompt','embedding','prompt_rehashed'):
                    raw=p/'matrix/rows.jsonl';rows=[json.loads(x) for x in raw.read_text().splitlines()]
                    rows[0][{'answer':'answer','prompt':'prompt','embedding':'embedding_model','prompt_rehashed':'prompt'}[condition]]='changed'
                    raw.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                    if condition=='prompt_rehashed':
                        review=p/'reviews.csv'
                        with review.open() as f: records=list(csv.DictReader(f))
                        records[0]['evidence_sha256']=fingerprint(rows[0])
                        with review.open('w',newline='') as f:
                            w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
                elif condition=='duplicate':
                    review=p/'reviews.csv';lines=review.read_text().splitlines();review.write_text('\n'.join(lines+[lines[1]])+'\n')
                elif condition in ('generator','scaling_query_digest'):
                    raw=p/'scaling/manifest.json';m=json.loads(raw.read_text());m['generator' if condition=='generator' else 'query_digest']='changed';raw.write_text(json.dumps(m))
                else:
                    for exp in ('matrix','scaling'):
                        raw=p/exp/'manifest.json';m=json.loads(raw.read_text());m['revision']='changed';raw.write_text(json.dumps(m))
                with self.assertRaises(ValueError): evaluation_table(p)
