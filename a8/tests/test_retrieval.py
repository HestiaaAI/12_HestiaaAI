import tempfile
import unittest
from pathlib import Path
import numpy as np
from a8.corpus import Chunk
from a8.retrieval import RetrievalIndex, build_index, search, save_index, load_index, score_retrieval


class Encoder:
    def encode(self, texts, **kwargs):
        return np.array([{'alpha': [1., 0.], 'beta': [0., 2.],
                          'duplicate': [2., 0.], 'question': [3., 0.]}[t] for t in texts])


def chunks():
    return [Chunk('a', 'doc', 'topic', ('p1',), 'alpha'),
            Chunk('b', 'doc', 'topic', ('p2',), 'beta'),
            Chunk('c', 'doc', 'topic', ('p1',), 'duplicate')]


class RetrievalTests(unittest.TestCase):
    def test_cosine_ranking_ties_and_metadata(self):
        index = build_index(chunks(), Encoder(), {'model': 'test'})
        hits = search(index, 'question', Encoder(), 3)
        self.assertEqual([h['chunk_id'] for h in hits], ['a', 'c', 'b'])
        self.assertEqual([h['score'] for h in hits], [1., 1., 0.])
        self.assertEqual(hits[0]['text'], 'alpha')
        self.assertEqual(hits[0]['paragraph_ids'], ['p1'])
        self.assertEqual(len(search(index, 'question', Encoder(), 10)), 3)

    def test_roundtrip_and_stale_index(self):
        index = build_index(chunks(), Encoder(), {'model': 'test'})
        with tempfile.TemporaryDirectory() as d:
            save_index(index, Path(d))
            loaded = load_index(Path(d), index.manifest)
            self.assertEqual(search(index, 'question', Encoder()), search(loaded, 'question', Encoder()))
            with self.assertRaises(ValueError):
                load_index(Path(d), {**index.manifest, 'model': 'changed'})
            # Reordering metadata without updating manifest must also be rejected.
            import json
            p = Path(d) / 'chunks.json'
            p.write_text(json.dumps(list(reversed(json.loads(p.read_text())))))
            with self.assertRaises(ValueError):
                load_index(Path(d), index.manifest)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            build_index([], Encoder(), {})
        index = build_index(chunks(), Encoder(), {})
        for query, k in [('', 3), (' ', 3), ('question', 0), ('question', -1)]:
            with self.subTest(query=query, k=k), self.assertRaises(ValueError):
                search(index, query, Encoder(), k)
        class BadEncoder:
            def __init__(self, vector): self.vector = vector
            def encode(self, texts, **kwargs): return np.tile(self.vector, (len(texts), 1))
        for v in [[0., 0.], [float('nan'), 1.], [float('inf'), 1.]]:
            with self.subTest(vector=v), self.assertRaises(ValueError):
                build_index(chunks(), BadEncoder(v), {})
        with self.assertRaises(ValueError):
            search(index, 'question', BadEncoder([1., 0., 0.]))

    def test_evidence_coverage_requires_actual_text(self):
        q = {'supporting_paragraph_ids': ['p1'], 'supporting_quotes': ['missing fact']}
        hits = search(build_index(chunks(), Encoder(), {}), 'question', Encoder())
        metrics = score_retrieval(hits, q)
        self.assertEqual(metrics['source_recall_at_k'], 1.)
        self.assertEqual(metrics['evidence_quote_coverage'], 0.)
        q['supporting_quotes'] = ['alpha', 'duplicate']
        self.assertEqual(score_retrieval(hits, q)['evidence_quote_coverage'], 1.)


if __name__ == '__main__': unittest.main()

class ModelSafetyTests(unittest.TestCase):
    def test_context_overflow_rejected(self):
        class Limited(Encoder):
            max_seq_length=2
            def tokenizer(self,texts,**kwargs): return {'input_ids':[[1,2,3] for _ in texts]}
        with self.assertRaisesRegex(ValueError,'exceeds embedding context'):
            build_index(chunks(),Limited(),{})

    def test_query_only_instruction_and_encoder_match(self):
        class Prefixed(Encoder):
            a8_metadata={'model_id':'test','query_prefix':'instruction: '}
            def encode(self,texts,**kwargs):
                return super().encode([t.removeprefix('instruction: ') for t in texts],**kwargs)
        encoder=Prefixed()
        index=build_index(chunks(),encoder,encoder.a8_metadata)
        self.assertEqual(search(index,'question',encoder)[0]['chunk_id'],'a')
        encoder.a8_metadata={**encoder.a8_metadata,'model_id':'different'}
        with self.assertRaisesRegex(ValueError,'does not match'):
            search(index,'question',encoder)
