"""Protect the completed 50 rows while validating the final approved-account run."""
import csv
import io
import json
import hashlib
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path
from a7.architecture_import_llama import ROOT,MODEL,CSV,ENV,import_results,verified_rows


class LlamaImportTests(unittest.TestCase):
    def fixture(self,root,alter=False):
        names=['__init__.py','benchmark_contract.py','benchmark_runner.py','review_results.py',
               'architecture/llama_review_audit.json','results/architecture_benchmark_environment.json']
        for name in names:
            dest=root/'a7'/name;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/'a7'/name,dest)
        canonical=root/'a7/results/architecture_benchmark.csv'
        canonical.write_bytes((ROOT/'a7/results/architecture_before_llama_colab.csv').read_bytes())
        raw=(ROOT/'a7/results'/CSV).read_bytes()
        environment=json.loads((ROOT/'a7/results'/ENV).read_text())
        if alter:
            rows=list(csv.DictReader(io.StringIO(raw.decode())))
            rows[0]['prompt']='Changed input'
            out=io.StringIO();writer=csv.DictWriter(out,fieldnames=list(rows[0]))
            writer.writeheader();writer.writerows(rows);raw=out.getvalue().encode()
            environment['result_csv_sha256']=hashlib.sha256(raw).hexdigest()
        bundle=root/'llama.zip'
        with zipfile.ZipFile(bundle,'w') as archive:
            archive.writestr(CSV,raw);archive.writestr(ENV,json.dumps(environment))
        return canonical,bundle

    def test_import_preserves_prior_fifty_and_original_raw_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);canonical,bundle=self.fixture(root)
            before=canonical.read_bytes()
            expected=[r for r in csv.DictReader(io.StringIO(before.decode())) if r['model_id']!=MODEL]
            rows=import_results(bundle,ROOT/'a7/architecture_llama_colab.ipynb',root)
            self.assertEqual(len(rows),75)
            self.assertEqual([r for r in rows if r['model_id']!=MODEL],expected)
            self.assertEqual((root/'a7/results/architecture_before_llama_colab.csv').read_bytes(),before)
            self.assertEqual((root/'a7/results'/CSV).read_bytes(),(ROOT/'a7/results'/CSV).read_bytes())
            self.assertEqual(sum(r['status']=='ok' for r in rows),75)
            self.assertTrue(all(1<=int(r['self_evaluation_score_1_to_10'])<=10 for r in rows))

    def test_changed_prompt_is_rejected_before_mutating_matrix(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);canonical,bundle=self.fixture(root,alter=True);before=canonical.read_bytes()
            with self.assertRaisesRegex(ValueError,'exact-contract'):
                import_results(bundle,ROOT/'a7/architecture_llama_colab.ipynb',root)
            self.assertEqual(canonical.read_bytes(),before)


    def test_standard_review_rebuild_retains_inspected_llama_scores(self):
        import a7.architecture_review as review
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);canonical,bundle=self.fixture(root)
            import_results(bundle,ROOT/'a7/architecture_llama_colab.ipynb',root)
            for name in ['response_review_reference.json','tinyllama_review_notes.json','tinyllama_review_reference.json']:
                shutil.copyfile(ROOT/'a7/architecture'/name,root/'a7/architecture'/name)
            with canonical.open(encoding='utf-8') as source:
                expected=list(csv.DictReader(source))
            with patch.object(review,'ROOT',root):review.main()
            with canonical.open(encoding='utf-8') as source:
                self.assertEqual(list(csv.DictReader(source)),expected)

    def test_review_hash_accepts_only_line_ending_conversion(self):
        from a7.architecture_review import matches_review_hash
        response='a household fact.\nnext line.'
        digest=hashlib.sha256(response.encode()).hexdigest()
        self.assertTrue(matches_review_hash(response.replace('\n','\r\n'),digest))
        self.assertFalse(matches_review_hash(response+' ',digest))
        self.assertFalse(matches_review_hash(response.replace('fact','fiction'),digest))
