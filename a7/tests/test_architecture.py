"""Guard against misleading aggregation and cost comparison results."""
import csv
import json
import tempfile
from pathlib import Path
import unittest

from a7.benchmark_contract import MODEL_REGISTRY
from a7.architecture_analysis import TRAFFIC, benchmark_evidence, compare_costs, crossover_intervals, routing_simulation, api_rate_frontier
from a7.architecture_comparison import comparison_markdown


class ArchitectureTests(unittest.TestCase):
    def test_missing_evidence_is_not_zero_cost_or_completed_benchmark(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, coverage = benchmark_evidence(root)
            self.assertEqual(int(coverage.missing.sum()), 375)
            costs, status = compare_costs(root/'local.csv', root/'api.csv')
            self.assertTrue(costs.empty)
            self.assertIn('Pending', status)

    def test_workload_mismatch_is_rejected_and_crossings_are_bracketed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows = [dict(model_id=m['model_id'], traffic_category=t, daily_active_users=d,
                         requests_per_user=1, input_tokens_per_request=100,
                         output_tokens_per_request=500, total_daily_cost_usd=10,
                         assumptions_id='test-only', source_or_assumption='synthetic unit test')
                    for m in MODEL_REGISTRY for t,d in TRAFFIC.items()]
            def write(name, data):
                with (root/name).open('w', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(data[0]))
                    writer.writeheader(); writer.writerows(data)
            write('local.csv', rows)
            api = [dict(r, total_daily_cost_usd=5 if r['daily_active_users'] < 100000 else 20) for r in rows]
            write('api.csv', api)
            costs, _ = compare_costs(root/'local.csv', root/'api.csv')
            intervals = crossover_intervals(costs)
            self.assertEqual(len(intervals), 15)
            self.assertEqual(set(intervals.lower_dau), {10000})
            self.assertEqual(set(intervals.upper_dau), {100000})
            api[0]['requests_per_user'] = 2
            write('api.csv', api)
            with self.assertRaisesRegex(ValueError, 'workload'):
                compare_costs(root/'local.csv', root/'api.csv')
            frontier=api_rate_frontier(root/'local.csv')
            self.assertEqual(len(frontier),90)
            prototype=frontier[frontier.daily_active_users.eq(1000)]
            self.assertTrue((prototype.api_blended_rate_break_even_usd_per_million_output_tokens==20).all())
            with self.assertRaisesRegex(ValueError,'nonnegative'):
                api_rate_frontier(root/'local.csv',gateway_daily_cost_usd=-1)

    def test_routing_load_is_conserved(self):
        rows = routing_simulation()
        self.assertEqual(len(rows), 30)
        for row in rows.to_dict('records'):
            self.assertAlmostEqual(row['cached_requests'] + row['local_requests'] + row['api_requests'],
                                   row['daily_active_users'])

    def test_comparison_selects_k_and_rejects_changed_rag_weights(self):
        manifest_path = Path(__file__).resolve().parents[1]/'slm/results/selected_checkpoint.json'
        manifest = json.loads(manifest_path.read_text())
        original = manifest['state_sha256']
        def response(state=original):
            return dict(prompt='students ', response='synthetic unit test only', state_sha256=state,
                        factual_accuracy=3, relevance=3, unsupported_information=False,
                        review_notes='Synthetic validation fixture, not experiment evidence.')
        questions = []
        for i in range(5):
            rag = [dict(response(), top_k=k, retrieved_document_ids=list(range(k)),
                        visible_context='students ', factual_accuracy=k+3) for k in (1,2,3,5)]
            questions.append(dict(question_id=str(i), question='synthetic question',
                                  expected_facts=['test fixture'], source_document_ids=['test'],
                                  baseline=response(), fine_tuned=response('f'*64), rag=rag))
        evidence = dict(original_state_sha256=original,
                        generation={**manifest['generation'], 'device':'cpu', 'threads':2},
                        questions=questions)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'comparison.json'
            path.write_text(json.dumps(evidence))
            self.assertIn('Top-K = 5', comparison_markdown(path, manifest_path))
            questions[0]['rag'][0]['state_sha256'] = 'e'*64
            path.write_text(json.dumps(evidence))
            with self.assertRaisesRegex(ValueError, 'preserve original weights'):
                comparison_markdown(path, manifest_path)

    def test_supplied_rag_appears_without_fabricating_fine_tuning(self):
        root=Path(__file__).resolve().parents[1]
        text=comparison_markdown(root/'architecture/inputs/slm_comparison.json',
                                 root/'slm/results/selected_checkpoint.json')
        self.assertIn('when is laundry day.',text)
        self.assertIn('RAG Top-K = 1',text)
        self.assertIn('Pending fine-tuning evidence',text)
        self.assertIn('No fine-tuned weights or outputs were supplied',text)
        self.assertNotIn('awaiting shared question',text)


if __name__ == '__main__':
    unittest.main()
