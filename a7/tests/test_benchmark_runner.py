import unittest

from a7.benchmark_contract import MODEL_REGISTRY, PROMPTS
from a7.benchmark_runner import RESULT_COLUMNS, expected_keys, select_models, validate_result_rows


class BenchmarkRunnerTests(unittest.TestCase):
    def test_person_one_selection_has_four_models_across_four_categories(self):
        models = select_models(owner="P1")
        self.assertEqual(len(models), 4)
        self.assertEqual(len({model["category"] for model in models}), 4)

    def test_expected_person_one_matrix_has_one_hundred_unique_rows(self):
        models = select_models(owner="P1")
        keys = expected_keys(models, PROMPTS)
        self.assertEqual(len(keys), 100)
        self.assertEqual(len(set(keys)), 100)

    def test_explicit_model_selection_rejects_unknown_id(self):
        with self.assertRaisesRegex(ValueError, "Unknown model"):
            select_models(model_ids=["not/a-real-model"])

    def test_result_validation_accepts_complete_matrix(self):
        rows = []
        for model in MODEL_REGISTRY[:1]:
            for prompt in PROMPTS:
                row = {column: "" for column in RESULT_COLUMNS}
                row.update({"model_id": model["model_id"], "prompt_id": prompt["prompt_id"], "status": "ok"})
                rows.append(row)
        validate_result_rows(rows, MODEL_REGISTRY[:1], PROMPTS)

    def test_result_validation_rejects_duplicate_keys(self):
        model = MODEL_REGISTRY[0]
        prompt = PROMPTS[0]
        row = {column: "" for column in RESULT_COLUMNS}
        row.update({"model_id": model["model_id"], "prompt_id": prompt["prompt_id"], "status": "ok"})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_result_rows([row, row.copy()], [model], [prompt])


if __name__ == "__main__":
    unittest.main()
