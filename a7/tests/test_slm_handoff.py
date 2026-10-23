"""Checks for source fidelity, causal attention and safe shared generation."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
import torch
from a7.slm.class_model import TinyTransformerLM
from a7.slm.handoff import generate, load_selected, state_hash

ROOT = Path(__file__).resolve().parents[1] / 'slm'


class SLMHandoffTests(unittest.TestCase):
    def test_classes_are_identical_to_professors_source(self):
        notebook = json.loads((ROOT / 'class_source.ipynb').read_text())
        original = '\n'.join(''.join(notebook['cells'][i]['source']) for i in (20,21))
        extracted = ast.parse((ROOT / 'class_model.py').read_text())
        self.assertEqual(
            [ast.dump(n) for n in ast.parse(original).body if isinstance(n,ast.ClassDef)],
            [ast.dump(n) for n in extracted.body if isinstance(n,ast.ClassDef)])

    def test_reload_causality_and_generation_without_weight_changes(self):
        torch.set_num_threads(2)
        config=dict(embedding_dim=48,num_heads=2,num_layers=1,feedforward_dim=192,context_length=32)
        vocab=list(' abcdefghijklmnopqrstuvwxyz.\n')
        model=TinyTransformerLM(vocab_size=len(vocab),**config).eval()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.pt'
            torch.save(dict(model_state=model.state_dict(),vocab=vocab,config=config),path)
            loaded, chars=load_selected(path)
        initial=state_hash(loaded)
        self.assertEqual(initial,state_hash(model))
        x=torch.zeros((1,32),dtype=torch.long)
        changed=x.clone(); changed[:,16:]=1
        with torch.no_grad():
            self.assertTrue(torch.allclose(loaded(x)[:,:16],loaded(changed)[:,:16],atol=1e-6))
        self.assertEqual(generate(loaded,chars,'students ',max_new_tokens=10),
                         generate(loaded,chars,'students ',max_new_tokens=10))
        self.assertEqual(initial,state_hash(loaded))
        with self.assertRaisesRegex(ValueError,'absent'):
            generate(loaded,chars,'Hello?')
