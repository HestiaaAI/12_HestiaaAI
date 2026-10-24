"""Check the optional Colab loader without downloading weights or requiring CUDA."""
import unittest
from unittest.mock import Mock
from a7.benchmark_runner import load_model


class QuantizedLoaderTests(unittest.TestCase):
    def test_native_keeps_existing_loading_and_device_move(self):
        auto, bits = Mock(), Mock()
        model = load_model('example/model', 'cpu', 'float32', 'none', auto, bits)
        auto.from_pretrained.assert_called_once_with('example/model', dtype='float32', low_cpu_mem_usage=True)
        model.to.assert_called_once_with('cpu')
        bits.assert_not_called()

    def test_nf4_uses_cuda_device_map_and_never_moves_quantized_model(self):
        auto, bits = Mock(), Mock()
        model = load_model('example/model', 'cuda', 'float32', 'nf4', auto, bits)
        bits.assert_called_once_with(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                                    bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype='float32')
        self.assertEqual(auto.from_pretrained.call_args.kwargs['device_map'], {'': 0})
        model.to.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'CUDA'):
            load_model('example/model', 'cpu', 'float32', 'nf4', auto, bits)
