import csv
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from a7.person2.local_costs import ROOT,build_tables,capacity_rate,machines_needed
from a7.person2.review_benchmarks import reviewed_rows,RAW,AUDIT


class Person2CostReviewTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/'a7/person2/cost_assumptions.json').read_text())
        with RAW.open(newline='') as f:self.raw=list(csv.DictReader(f))

    def test_ninety_cases_ceilings_itemization_and_sensitivity(self):
        costs,rates,sensitivity=build_tables(self.config,self.raw)
        self.assertEqual(len(costs),90)
        self.assertEqual(len({(r['model_id'],r['traffic_category']) for r in costs}),90)
        self.assertEqual(len(rates),15);self.assertEqual(len(sensitivity),270)
        for r in costs:
            self.assertEqual(r['total_daily_output_tokens'],r['daily_active_users']*500)
            expected=max(1,math.ceil(r['total_daily_output_tokens']*2*1.25/(86400*(next(x['planning_tokens_per_second'] for x in rates if x['model_id']==r['model_id']))*.6)))
            self.assertEqual(r['machines_needed'],expected)
            self.assertAlmostEqual(r['total_daily_cost_usd'],expected*(12+10/30),places=5)
            self.assertLessEqual(r['planning_memory_gb'],24)
        for model in {r['model_id'] for r in costs}:
            subset=[r['total_daily_cost_usd'] for r in costs if r['model_id']==model]
            self.assertEqual(subset,sorted(subset))
        for r in costs:
            subset={x['rate_factor']:x['machines_needed'] for x in sensitivity
                    if x['model_id']==r['model_id'] and x['traffic_category']==r['traffic_category']}
            self.assertGreaterEqual(subset[.5],subset[1.]);self.assertGreaterEqual(subset[1.],subset[2.])

    def test_machine_rounding_and_invalid_capacity(self):
        config=copy.deepcopy(self.config);config.update(peak_to_average=1,target_utilization=1,service_time_penalty=1)
        self.assertEqual(machines_needed(86400,1,config),1)
        self.assertEqual(machines_needed(86401,1,config),2)
        self.assertEqual(machines_needed(0,1,config),1)
        with self.assertRaises(ValueError):machines_needed(1,0,config)
        config['target_utilization']=0
        with self.assertRaises(ValueError):machines_needed(1,1,config)
        self.assertEqual(capacity_rate(1,[(1,10),(4,2)]),10)
        self.assertAlmostEqual(capacity_rate(2,[(1,10),(4,2)]),math.sqrt(20))

    def test_all_assessments_preserve_raw_and_enforce_hashes(self):
        rows=reviewed_rows();self.assertEqual(len(rows),100)
        fields=json.loads(AUDIT.read_text())['component_order']
        for old,new in zip(self.raw,rows):
            for col in old:
                if col not in fields+['self_evaluation_score_1_to_10','review_notes']:
                    self.assertEqual(old[col],new[col])
            self.assertEqual(new['self_evaluation_score_1_to_10'],max(1,sum(new[f] for f in fields)))
            self.assertIn('AI-assisted',new['review_notes'])
        with tempfile.TemporaryDirectory() as tmp:
            changed=Path(tmp)/'changed.csv';changed.write_bytes(RAW.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'Raw evidence changed'):reviewed_rows(changed)
        self.assertTrue(all(not r['self_evaluation_score_1_to_10'] for r in self.raw))
