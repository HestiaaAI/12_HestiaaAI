"""Benchmark provenance/checkpoint tests: no model downloads or GPU required."""
import ast
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('p4_large',ROOT/'llm-test/person4_large_benchmark.py')
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class LargerBenchmarkTests(unittest.TestCase):
    def test_changed_contract_is_not_executed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            (path/'team_contract.py').write_text('raise AssertionError("must never execute")',encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError,'SHA-256 mismatch'):
                runner.shared_contract(path)

    def test_atomic_csv_preserves_raw_multiline_unicode(self):
        row={'model_id':'model','raw_output':'{"tasks":[] }\nUnicode: café, "quoted"'}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'results.csv'
            runner.persist([row],list(row),path)
            with path.open(encoding='utf-8',newline='') as handle:
                self.assertEqual(list(csv.DictReader(handle)),[row])
            self.assertFalse(path.with_suffix('.tmp').exists())

    def test_pinned_team_contract_has_eight_fixed_cases(self):
        source=subprocess.check_output(['git','show',runner.CONTRACT_COMMIT+':docs/a6-person-2/run_shivani_contract_benchmark.py'],cwd=ROOT)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            (path/'team_contract.py').write_bytes(source)
            contract=runner.shared_contract(path)
            self.assertEqual(len(contract.TEST_INPUTS)*len(contract.SHOT_MODES),8)
            self.assertEqual(len(contract.CSV_FIELDS),11)
            self.assertEqual(contract.SHOT_MODES,['zero','one','few','many'])

    def test_colab_contains_exact_checked_in_runner(self):
        notebook=json.loads((ROOT/'llm-test/person4_large_models_colab.ipynb').read_text(encoding='utf-8'))
        embedded=[]
        for cell in notebook['cells']:
            source=''.join(cell.get('source',[]))
            if cell['cell_type']!='code' or source.startswith('# Environment setup'):
                continue
            for node in ast.walk(ast.parse(source)):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='write_text':
                    if isinstance(node.func.value,ast.Name) and node.func.value.id=='RUNNER':
                        embedded.append(ast.literal_eval(node.args[0]))
        self.assertEqual(embedded,[(ROOT/'llm-test/person4_large_benchmark.py').read_text(encoding='utf-8')])

    def test_large_models_do_not_duplicate_teammates(self):
        completed=set()
        for person in (1,2,3):
            with (ROOT/f'a6_results/person{person}_benchmark_results.csv').open(encoding='utf-8',newline='') as handle:
                completed.update(row['model_id'] for row in csv.DictReader(handle))
        self.assertFalse(completed.intersection(runner.MODELS))
        self.assertEqual(len(set(runner.MODELS)),4)


if __name__=='__main__':
    unittest.main()
