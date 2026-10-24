import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from a7.slm.rag_experiment import build_index, retrieve, pack_prompt, validate_text, run_experiments

ROOT = Path(__file__).resolve().parents[1]


class Person2RagTests(unittest.TestCase):
    def setUp(self):
        self.documents = json.loads((ROOT / 'slm/knowledge_base/documents.json').read_text())
        self.questions = json.loads((ROOT / 'slm/knowledge_base/questions.json').read_text())
        self.vocab = json.loads((ROOT / 'slm/results/selected_checkpoint.json').read_text())['vocab']
        self.vectorizer, self.matrix = build_index(self.documents)

    def test_retrieval_body_matches_class_source(self):
        source = json.loads((ROOT / 'slm/class_rag_source.ipynb').read_text())
        original = next(n for n in ast.parse(''.join(source['cells'][14]['source'])).body
                        if isinstance(n, ast.FunctionDef) and n.name == 'retrieve')
        module = ast.parse((ROOT / 'slm/rag_experiment.py').read_text())
        adapted = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'retrieve')
        self.assertEqual([ast.dump(n) for n in original.body], [ast.dump(n) for n in adapted.body])

    def test_every_top_k_is_exact_and_primary_source_ranks_first(self):
        for question in self.questions:
            for k in (1, 2, 3, 5):
                matches = retrieve(question['question'], self.documents, self.vectorizer, self.matrix, top_k=k)
                self.assertEqual(len(matches), k)
                self.assertEqual(matches[0]['id'], question['source_document_ids'][0])
                self.assertEqual(len({d['id'] for d in matches}), k)
                self.assertEqual([d['score'] for d in matches], sorted([d['score'] for d in matches], reverse=True))

    def test_packed_context_preserves_only_supported_characters(self):
        question = self.questions[0]['question']
        matches = retrieve(question, self.documents, self.vectorizer, self.matrix, top_k=5)
        prompt = pack_prompt(question, matches)
        validate_text(prompt, self.vocab)
        self.assertTrue(prompt.endswith(question + '\n'))
        self.assertEqual(len(prompt[-32:]), 32)
        self.assertLess(len(prompt[-32:]), len(prompt))
        with self.assertRaises(ValueError):
            validate_text('Question?', self.vocab)

    def test_exports_five_baselines_twenty_rag_rows_without_generating_locally(self):
        manifest = json.loads((ROOT / 'slm/results/selected_checkpoint.json').read_text())
        fake_model = object()
        with tempfile.TemporaryDirectory() as tmp, \
             patch('a7.slm.rag_experiment.load_selected', return_value=(fake_model, self.vocab)), \
             patch('a7.slm.rag_experiment.state_hash', return_value=manifest['state_sha256']), \
             patch('a7.slm.rag_experiment.verify_checkpoint'), \
             patch('a7.slm.rag_experiment.generate', side_effect=lambda model,vocab,prompt,**kw: prompt+'actual test continuation') as generator:
            result = run_experiments(Path('ignored-test.pt'), Path(tmp))
            self.assertEqual(generator.call_count, 25)
            self.assertTrue(result['weights_unchanged'])
            self.assertEqual(len(result['questions']), 5)
            for question in result['questions']:
                self.assertEqual(question['baseline']['response'], 'actual test continuation')
                self.assertEqual([r['top_k'] for r in question['rag']], [1, 2, 3, 5])
                for row in question['rag']:
                    self.assertEqual(row['visible_context'], row['prompt'][-32:])
                    self.assertIsNone(row['factual_accuracy'])

    def test_weight_change_is_rejected(self):
        manifest = json.loads((ROOT / 'slm/results/selected_checkpoint.json').read_text())
        calls = iter([manifest['state_sha256'], 'changed'])
        with tempfile.TemporaryDirectory() as tmp, \
             patch('a7.slm.rag_experiment.load_selected', return_value=(object(), self.vocab)), \
             patch('a7.slm.rag_experiment.state_hash', side_effect=lambda _: next(calls)), \
             patch('a7.slm.rag_experiment.verify_checkpoint'), \
             patch('a7.slm.rag_experiment.generate', side_effect=lambda model,vocab,prompt,**kw: prompt+'test'):
            with self.assertRaisesRegex(ValueError, 'weights changed'):
                run_experiments(Path('ignored-test.pt'), Path(tmp))
            self.assertFalse((Path(tmp)/'person2_rag.json').exists())


if __name__ == '__main__':
    unittest.main()
