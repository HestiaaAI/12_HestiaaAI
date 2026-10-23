import unittest

from a7.benchmark_contract import (
    EVALUATION_CRITERIA,
    MODEL_REGISTRY,
    PROMPTS,
    validate_contract,
)


class BenchmarkContractTests(unittest.TestCase):
    def test_contract_is_valid(self):
        validate_contract()

    def test_roster_reuses_exactly_fifteen_models(self):
        self.assertEqual(len(MODEL_REGISTRY), 15)
        self.assertEqual(len({model["model_id"] for model in MODEL_REGISTRY}), 15)

    def test_each_size_category_has_three_models(self):
        counts = {}
        for model in MODEL_REGISTRY:
            counts[model["category"]] = counts.get(model["category"], 0) + 1
        self.assertEqual(sorted(counts.values()), [3, 3, 3, 3, 3])

    def test_member_allocation_is_four_four_four_three(self):
        counts = {}
        for model in MODEL_REGISTRY:
            counts[model["owner"]] = counts.get(model["owner"], 0) + 1
        self.assertEqual(counts, {"P1": 4, "P2": 4, "P3": 4, "architecture": 3})

    def test_prompt_matrix_has_five_types_and_five_prompts_each(self):
        counts = {}
        for prompt in PROMPTS:
            counts[prompt["prompt_type"]] = counts.get(prompt["prompt_type"], 0) + 1
        self.assertEqual(len(PROMPTS), 25)
        self.assertEqual(sorted(counts.values()), [5, 5, 5, 5, 5])
        self.assertEqual(len({prompt["prompt_id"] for prompt in PROMPTS}), 25)

    def test_manual_scoring_rubric_totals_ten_points(self):
        self.assertEqual(sum(item["max_points"] for item in EVALUATION_CRITERIA), 10)


if __name__ == "__main__":
    unittest.main()
