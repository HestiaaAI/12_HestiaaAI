"""P4 category correction: four real local-to-GPU Transformers benchmarks.

Uses the unchanged P1/P2 prompt/schema contract; NF4 weight quantization with
FP32 compute and non-quantized modules. No paid provider, no fine-tuning.
Each model runs in its own process when launched by the accompanying notebook.
"""
import argparse
import csv
import gc
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import platform
import time
from datetime import datetime, timezone

MODELS = [
    "tiiuae/Falcon3-7B-Instruct",
    "Qwen/Qwen2.5-14B-Instruct",
    "microsoft/Phi-3-medium-4k-instruct",
    "Qwen/Qwen3-14B",
]
CONTRACT_SHA256 = "8403f9e97778af00d8b389cb8dce2a9d8fa94747cb737820883c4623c83cd459"
CONTRACT_COMMIT = "14a02aeb4eb71d1ddf7dfb66d1e868b77213eb28"


def shared_contract(folder):
    """Load pinned team-owned Python helpers, not model-generated code."""
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / "team_contract.py"
    if not source.exists():
        import requests
        url = ("https://raw.githubusercontent.com/HestiaaAI/12_HestiaaAI/"
               f"{CONTRACT_COMMIT}/docs/a6-person-2/run_shivani_contract_benchmark.py")
        response = requests.get(url, timeout=45)
        response.raise_for_status()
        source.write_bytes(response.content)
    if hashlib.sha256(source.read_bytes()).hexdigest() != CONTRACT_SHA256:
        raise RuntimeError("Shared contract SHA-256 mismatch; refusing to run changed prompts")
    spec = importlib.util.spec_from_file_location("hestia_shared_contract", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def persist(rows, fields, csv_path):
    temporary = csv_path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(csv_path)


def run(model_id, output):
    import torch
    import transformers
    import bitsandbytes
    import psutil
    from huggingface_hub import HfApi
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    output.mkdir(parents=True, exist_ok=True)
    team = shared_contract(output / "support")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required. This is not a completed benchmark on CPU.")
    gpu = torch.cuda.get_device_properties(0)
    free, total = torch.cuda.mem_get_info()
    if free < 13.0 * 2**30 and "14B" in model_id:
        raise RuntimeError(f"Need at least 13 GiB free VRAM for this 14B configuration; available {free/2**30:.2f} GiB")
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.set_num_threads(2)
    csv_path = output / "person4_large_results.csv"
    rows = []
    if csv_path.exists():
        with csv_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    done = {(row["model_id"], row["input_id"], row["shot_mode"]) for row in rows}
    expected = {(model_id, key, shot) for key in team.TEST_INPUTS for shot in team.SHOT_MODES}
    if expected <= done:
        print("All eight actual generations already checkpointed for", model_id, flush=True)
        return
    sha = HfApi().model_info(model_id).sha
    metadata_path = output / "person4_large_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {"models": {}}
    previous = metadata["models"].get(model_id, {})
    sha = previous.get("revision", sha)
    metadata.update({"created_at_utc": metadata.get("created_at_utc", datetime.now(timezone.utc).isoformat()),
        "python": platform.python_version(), "torch": torch.__version__, "transformers": transformers.__version__,
        "bitsandbytes": bitsandbytes.__version__, "device": "cuda:0", "gpu": gpu.name,
        "vram_gib": round(total/2**30, 3), "host_ram_gib": round(psutil.virtual_memory().total/2**30, 3),
        "quantization": "4-bit NF4 weights with double quantization",
        "compute_dtype": "float32", "non_quantized_dtype": "float32", "attention": "eager",
        "max_new_tokens": 220, "do_sample": False, "seed": 0, "contract_sha256": CONTRACT_SHA256,
        "timing_note": "Load includes initial downloads when uncached; generation synchronized on CUDA. Cross-hardware/precision speed comparisons are not controlled.",
        "review_attribution": "Unscored until raw-output content review; no generated or heuristic scores.",
        "configurations_comparable_to_native": False})
    metadata["models"][model_id] = {"revision": sha, "status": "loading", "qwen3_thinking": False if "Qwen3" in model_id else None}
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("Loading", model_id, "revision", sha, "on", gpu.name, flush=True)
    start = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=sha, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(model_id, revision=sha, trust_remote_code=False,
        dtype=torch.float32, device_map={"": 0}, low_cpu_mem_usage=True,
        attn_implementation="eager", quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float32))
    model.eval()
    torch.cuda.synchronize()
    load_seconds = time.perf_counter() - start
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    metadata["models"][model_id].update(status="generating", load_seconds=round(load_seconds,3),
                                         footprint_gib=round(model.get_memory_footprint()/2**30,3))
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    for input_id, text in team.TEST_INPUTS.items():
        for shot in team.SHOT_MODES:
            if (model_id, input_id, shot) in done:
                continue
            messages = [{"role":"system", "content":team.SYSTEM_INSTRUCTION},
                        {"role":"user", "content":team.build_user_prompt(text,shot)}]
            options = {"enable_thinking": False} if "Qwen3" in model_id else {}
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, **options)
            encoded = tokenizer(prompt, return_tensors="pt").to("cuda:0")
            forward_fields = inspect.signature(model.forward).parameters
            last_logit = ({"logits_to_keep": 1} if "logits_to_keep" in forward_fields else
                          {"num_logits_to_keep": 1} if "num_logits_to_keep" in forward_fields else {})
            with torch.inference_mode():
                probe = model(**encoded, use_cache=False, **last_logit)
                finite = bool(torch.isfinite(probe.logits[:, -1, :]).all())
                del probe
            if not finite:
                raise RuntimeError(f"Non-finite pre-generation logits: {model_id} {input_id}/{shot}; no output fabricated")
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
            start = time.perf_counter()
            with torch.inference_mode():
                generated = model.generate(**encoded, max_new_tokens=220, do_sample=False,
                    pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
            torch.cuda.synchronize()
            seconds = time.perf_counter() - start
            tokens = generated[0, encoded["input_ids"].shape[-1]:]
            raw = tokenizer.decode(tokens, skip_special_tokens=True).strip()
            try:
                errors = team.validate_payload(team.extract_json(raw))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                errors = [str(exc)]
            rows.append({"model_id":model_id, "input_id":input_id, "shot_mode":shot,
                "load_seconds":round(load_seconds,3), "generation_seconds":round(seconds,3),
                "output_tokens":int(tokens.numel()), "schema_valid":not errors,
                "validation_errors":" | ".join(errors), "raw_output":raw,
                "quality_score_0_to_10":"", "review_notes":"NF4 weights; FP32 compute/non-quantized modules; eager CUDA; pending raw-output review."})
            persist(rows,team.CSV_FIELDS,csv_path)
            metadata["models"][model_id].update(last_completed=f"{input_id}/{shot}",
                peak_allocated_gib=round(torch.cuda.max_memory_allocated()/2**30,3))
            metadata_path.write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
            print(f"CHECKPOINT {model_id} {input_id}/{shot}: {seconds:.3f}s; schema={not errors}; tokens={tokens.numel()}",flush=True)
            del generated, tokens, encoded
            gc.collect()
    metadata["models"][model_id].update(status="complete", completed_generations=8)
    metadata_path.write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    print("MODEL COMPLETE:",model_id,flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--model",choices=MODELS,required=True)
    parser.add_argument("--output",type=Path,default=Path("a6_results/person4_large"))
    args=parser.parse_args()
    run(args.model,args.output)
