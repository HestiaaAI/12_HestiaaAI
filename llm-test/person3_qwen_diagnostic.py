"""Isolated Qwen probe. Never overwrites benchmark CSVs or downloads credentials.

Run in the existing Colab bundle: python llm-test/person3_qwen_diagnostic.py
NF4 weights remain 4-bit; float32 computation tests a precision hypothesis.
This is diagnostic evidence, not a replacement benchmark or a confirmed fix.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

from person3_benchmark import NOTEBOOK, build_user_prompt, load_contract, validate_payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compute', choices=['float16', 'float32'], default='float32')
    args = parser.parse_args()
    output = Path(__file__).resolve().parent.parent / 'a6_results' / f'person3_qwen_probe_{args.compute}.json'
    output.parent.mkdir(exist_ok=True)
    # Reserve a fresh file before loading; an earlier diagnostic is never replaced.
    with output.open('x') as stream:
        record = {
            'kind': 'diagnostic_not_benchmark', 'model_id': 'Qwen/Qwen2.5-7B-Instruct',
            'input_id': 'BD1', 'shot_mode': 'one', 'precision': 'nf4',
            'compute_dtype': args.compute, 'non_quantized_dtype': args.compute,
            'attention': 'eager', 'double_quant': True,
            'max_new_tokens': 220, 'do_sample': False,
            'notebook_sha256': hashlib.sha256(NOTEBOOK.read_bytes()).hexdigest(),
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }
        failed = False
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            if not torch.cuda.is_available():
                raise RuntimeError('CUDA required')
            record.update(gpu=torch.cuda.get_device_name(0),
                          device_capacity_gib=torch.cuda.get_device_properties(0).total_memory / 1024**3,
                          versions={name: importlib.metadata.version(name) for name in
                                    ['torch', 'transformers', 'accelerate', 'bitsandbytes']})
            contract = load_contract()
            dtype = getattr(torch, args.compute)
            tokenizer = AutoTokenizer.from_pretrained(record['model_id'], trust_remote_code=False)
            model = AutoModelForCausalLM.from_pretrained(
                record['model_id'], torch_dtype=dtype, trust_remote_code=False,
                device_map={'': 0}, low_cpu_mem_usage=True, attn_implementation='eager',
                quantization_config=BitsAndBytesConfig(
                    load_in_4bit=True, bnb_4bit_quant_type='nf4',
                    bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=dtype))
            model.eval()
            messages = [
                {'role': 'system', 'content': contract['SYSTEM_INSTRUCTION']},
                {'role': 'user', 'content': build_user_prompt(contract, contract['TEST_INPUTS']['BD1'], 'one')},
            ]
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            record['rendered_prompt_sha256'] = hashlib.sha256(prompt.encode()).hexdigest()
            inputs = tokenizer(prompt, return_tensors='pt').to('cuda')
            torch.cuda.synchronize()
            started = time.perf_counter()
            with torch.inference_mode():
                result = model.generate(
                    **inputs, max_new_tokens=220, do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                    return_dict_in_generate=True, output_scores=True)
            torch.cuda.synchronize()
            record['generation_seconds'] = time.perf_counter() - started
            tokens = result.sequences[0, inputs['input_ids'].shape[1]:]
            raw = tokenizer.decode(tokens, skip_special_tokens=True).strip()
            record.update(raw_output=raw, output_tokens=len(tokens),
                          nan_score_steps=sum(bool(torch.isnan(s).any().item()) for s in result.scores),
                          positive_inf_score_steps=sum(bool(torch.isposinf(s).any().item()) for s in result.scores),
                          negative_inf_score_steps=sum(bool(torch.isneginf(s).any().item()) for s in result.scores),
                          peak_allocated_gib=torch.cuda.max_memory_allocated() / 1024**3)
            try:
                payload = json.loads(raw)
                record['validation_errors'] = validate_payload(contract, payload)
                record['strict_json'] = True
            except json.JSONDecodeError:
                record.update(strict_json=False, validation_errors=['Full output is not valid JSON'])
            record['schema_valid'] = record['strict_json'] and not record['validation_errors']
        except Exception as exc:
            # Avoid printing dependency exception bodies that may contain secrets.
            record.update(error_type=type(exc).__name__,
                          error='Diagnostic failed; inspect GPU memory and dependency compatibility.')
            failed = True
        finally:
            json.dump(record, stream, indent=2)
            stream.write('\n')
    print('Saved', output, flush=True)
    if failed:
        raise SystemExit(1)
    print(record['raw_output'], flush=True)
    print('Strict schema valid:', record['schema_valid'], flush=True)


if __name__ == '__main__':
    main()
