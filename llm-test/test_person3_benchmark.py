import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from person3_benchmark import (
    SHOT_COUNTS, build_user_prompt, estimated_memory_gib, extract_json,
    load_contract, load_model, model_rows, validate_payload,
)


class SharedContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = load_contract()

    def test_four_assigned_models_and_eight_runs_per_model(self):
        self.assertEqual(len(model_rows(self.contract)), 4)
        self.assertEqual(len(SHOT_COUNTS) * len(self.contract["TEST_INPUTS"]), 8)

    def test_prompt_is_identical_to_notebook_policy_for_all_shot_modes(self):
        for mode, count in SHOT_COUNTS.items():
            text = self.contract["TEST_INPUTS"]["BD1"]
            prompt = build_user_prompt(self.contract, text, mode)
            self.assertEqual(prompt.count("Example input:"), count)
            self.assertTrue(prompt.endswith(f"Household message: {text}\nJSON output:"))
            if count:
                self.assertTrue(prompt.startswith("Example input: " + self.contract["EXAMPLES"][0]["input"]))

    def test_parser_and_validator_match_notebook_examples(self):
        expected = self.contract["EXAMPLES"][0]["output"]
        self.assertEqual(validate_payload(self.contract, expected), [])
        self.assertEqual(extract_json("result: " + json.dumps(expected)), expected)
        with self.assertRaises(ValueError):
            extract_json('{"tasks":[],"tasks":[]}')
        self.assertTrue(validate_payload(self.contract, {"tasks": []}))

    def test_fp16_7b_needs_more_than_eight_gib(self):
        self.assertGreater(estimated_memory_gib(7.62, "mps"), 8)
        self.assertGreater(estimated_memory_gib(7.62, "cpu"), estimated_memory_gib(7.62, "mps"))

    def test_nf4_estimate_fits_t4_and_requires_cuda(self):
        self.assertLess(estimated_memory_gib(7.62, "cuda", "nf4"), 15)
        with self.assertRaises(ValueError):
            load_model("example/model", "cpu", "nf4")

    def test_nf4_loads_on_gpu_without_moving_quantized_model(self):
        model = Mock()
        factory = Mock()
        factory.from_pretrained.return_value = model
        config = Mock()
        fake_torch = SimpleNamespace(float16="fp16", float32="fp32")
        fake_transformers = SimpleNamespace(AutoModelForCausalLM=factory, BitsAndBytesConfig=config)
        with patch.dict("sys.modules", {"torch": fake_torch, "transformers": fake_transformers}):
            self.assertIs(load_model("example/model", "cuda", "nf4"), model)
        model.to.assert_not_called()
        config.assert_called_once_with(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                       bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype="fp16")
        self.assertEqual(factory.from_pretrained.call_args.kwargs["device_map"], {"": 0})
        self.assertTrue(factory.from_pretrained.call_args.kwargs["low_cpu_mem_usage"])

    def test_nf4_float32_uses_float32_for_compute_and_other_modules(self):
        factory, config = Mock(), Mock()
        with patch.dict("sys.modules", {
            "torch": SimpleNamespace(float16="fp16", float32="fp32"),
            "transformers": SimpleNamespace(AutoModelForCausalLM=factory, BitsAndBytesConfig=config),
        }):
            load_model("example/model", "cuda", "nf4", "float32")
        self.assertEqual(config.call_args.kwargs["bnb_4bit_compute_dtype"], "fp32")
        self.assertEqual(factory.from_pretrained.call_args.kwargs["torch_dtype"], "fp32")
        factory.from_pretrained.return_value.to.assert_not_called()

    def test_native_loading_still_moves_model_to_selected_device(self):
        factory = Mock()
        fake_torch = SimpleNamespace(float16="fp16", float32="fp32")
        fake_transformers = SimpleNamespace(AutoModelForCausalLM=factory)
        with patch.dict("sys.modules", {"torch": fake_torch, "transformers": fake_transformers}):
            model = load_model("example/model", "cpu", "native")
        model.to.assert_called_once_with("cpu")
        self.assertNotIn("quantization_config", factory.from_pretrained.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
