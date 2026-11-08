import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from a8.person2_experiments import run_retrieval_experiments, attach_generation


class Encoder:
    a8_metadata = {'model_id': 'deterministic-test-only', 'dimension': 4, 'revision': 'test', 'query_prefix': ''}
    def encode(self, texts, **kwargs):
        # Test vectors exercise bookkeeping, never substitute for measured HF embeddings.
        return np.array([[1., len(t) % 7, len(t) % 11, 1.] for t in texts], dtype=np.float32)


class ExperimentTests(unittest.TestCase):
    def test_matrix_scaling_exports_resume_and_config_guard(self):
        with tempfile.TemporaryDirectory() as d:
            rows = run_retrieval_experiments(Path(d), Encoder(), repetitions=1)
            matrix = [r for r in rows if r['experiment'] == 'matrix']
            scaling = [r for r in rows if r['experiment'] == 'scaling']
            self.assertEqual(len(matrix), 15)
            self.assertEqual(len(scaling), 10)
            self.assertEqual(len({(r['strategy'],r['query_id']) for r in matrix}),15)
            self.assertTrue(all(r['status'] == 'retrieval_only' and r['answer'] is None for r in rows))
            self.assertTrue(all(len(r['retrieved_chunks']) == 3 for r in rows))
            self.assertTrue(all(h['text'] and h['paragraph_ids'] for r in rows for h in r['retrieved_chunks']))
            self.assertEqual(len(run_retrieval_experiments(Path(d), Encoder(), repetitions=1)),25)
            with self.assertRaises(ValueError):
                run_retrieval_experiments(Path(d), Encoder(), top_k=2, repetitions=1)
            raw = Path(d)/'retrieval.jsonl'
            with raw.open('a') as f: f.write(json.dumps(rows[0])+'\n')
            with self.assertRaises(ValueError):
                run_retrieval_experiments(Path(d), Encoder(), repetitions=1)

    def test_answer_keys_never_reach_generator(self):
        with tempfile.TemporaryDirectory() as d:
            run_retrieval_experiments(Path(d), Encoder(), repetitions=1)
            calls=[]
            def generate(query, hits):
                calls.append((query,hits))
                self.assertIsInstance(query,str)
                self.assertTrue(all('expected_answer' not in h and 'supporting_quotes' not in h for h in hits))
                return {'answer': 'test output', 'prompt': 'test prompt', 'generation_ms': 1.,
                        'context_truncated': False}
            rows=attach_generation(Path(d), generate, {'generator':'test-only','revision':'1'})
            self.assertEqual(len(calls),25)
            self.assertTrue(all(r['status']=='generation_complete_review_pending' for r in rows))
            self.assertTrue(all(r['answer_quality'] is None for r in rows))
            # Identical configuration resumes; a different generator cannot reuse evidence.
            attach_generation(Path(d), generate, {'generator':'test-only','revision':'1'})
            self.assertEqual(len(calls),25)
            with self.assertRaises(ValueError):
                attach_generation(Path(d), generate, {'generator':'other'})


if __name__ == '__main__': unittest.main()

class GenerationSafetyTests(unittest.TestCase):
    def test_nonfinite_latency_and_truncated_context_saved_as_errors(self):
        for response in [dict(answer='x',prompt='p',generation_ms=float('nan'),context_truncated=False),
                         dict(answer='x',prompt='p',generation_ms=1,context_truncated=True)]:
            with self.subTest(response=response),tempfile.TemporaryDirectory() as d:
                run_retrieval_experiments(Path(d),Encoder(),repetitions=1)
                rows=attach_generation(Path(d),lambda q,h:response,{'generator':'test'})
                self.assertTrue(all(r['status']=='generation_error' for r in rows))
