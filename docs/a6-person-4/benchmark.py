"""P4 benchmarks: shared team prompts, three additional CPU-sized models.

Run from the repository: python docs/a6-person-4/benchmark.py
Results checkpoint after each response. No synthetic results or heuristic scores.
"""
import argparse
import csv
import gc
import hashlib
import importlib.util
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("HF_HOME", str(ROOT / "model_cache" / "huggingface"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

MODELS = ["Qwen/Qwen2-0.5B-Instruct", "HuggingFaceTB/SmolLM-360M-Instruct", "Qwen/Qwen3-0.6B"]
OUT = ROOT / "a6_results" / "person4_benchmark_results.csv"
META = ROOT / "a6_results" / "person4_environment.json"


def contract():
    spec = importlib.util.spec_from_file_location("team_contract", ROOT / "docs/a6-person-2/run_shivani_contract_benchmark.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def download_models():
    from huggingface_hub import HfApi, snapshot_download
    records = {}
    previous = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    for model_id in MODELS:
        print("Downloading public weights:", model_id, flush=True)
        sha = previous.get("models", {}).get(model_id, {}).get("revision") or HfApi().model_info(model_id).sha
        location = snapshot_download(model_id, revision=sha,
            local_dir=ROOT / "model_cache" / "models" / model_id.replace("/", "--"),
            max_workers=1, allow_patterns=[
            "*.json", "model.safetensors", "model-*.safetensors", "merges.txt", "vocab.json", "tokenizer.model"],
            ignore_patterns=["onnx/*", "onnx/**"])
        records[model_id] = {"revision": sha, "path": location}
    return records


def run(downloaded=None):
    import psutil
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    team = contract()
    torch.manual_seed(0)
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    snapshots = downloaded if downloaded is not None else download_models()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "generated_at_utc": (json.loads(META.read_text(encoding="utf-8")).get("generated_at_utc")
                             if META.exists() else datetime.now(timezone.utc).isoformat()),
        "python": platform.python_version(), "torch": torch.__version__,
        "transformers": transformers.__version__, "platform": platform.platform(),
        "device": "cpu", "dtype": "float32", "torch_threads": 4,
        "ram_gib": round(psutil.virtual_memory().total / 2**30, 2),
        "logical_processors": os.cpu_count(), "max_new_tokens": 220,
        "do_sample": False, "seed": 0,
        "models": {key: {"revision": val["revision"]} for key, val in snapshots.items()},
        "qwen3_thinking": False,
        "team_contract_sha256": hashlib.sha256((ROOT / "docs/a6-person-2/run_shivani_contract_benchmark.py").read_bytes()).hexdigest(),
        "notes": "Shared P1/P2 inputs, instructions, examples and schema. Qwen3 uses non-thinking chat template; greedy decoding follows team contract rather than vendor sampling guidance. CPU timings are not controlled cross-hardware comparisons. Quality scores require review of raw outputs.",
    }
    META.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    # Refuse accidentally reusing teammates' completed model IDs.
    completed = set()
    for source in OUT.parent.glob("person[123]_benchmark_results.csv"):
        with source.open(encoding="utf-8-sig", newline="") as handle:
            completed.update(row["model_id"] for row in csv.DictReader(handle) if row["input_id"] != "MODEL_LOAD")
    if completed.intersection(MODELS):
        raise RuntimeError("A selected model already appears in a teammate CSV")
    rows = []
    if OUT.exists():
        with OUT.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    done = {(row["model_id"], row["input_id"], row["shot_mode"]) for row in rows}
    for model_id in MODELS:
        if all((model_id, input_id, shot) in done for input_id in team.TEST_INPUTS for shot in team.SHOT_MODES):
            continue
        print("Loading", model_id, flush=True)
        start = time.perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(snapshots[model_id]["path"], local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(snapshots[model_id]["path"], dtype=torch.float32,
                                                    local_files_only=True, attn_implementation="eager")
        model.eval()
        load_seconds = time.perf_counter() - start
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token_id = tokenizer.eos_token_id
        for input_id, text in team.TEST_INPUTS.items():
            for shot in team.SHOT_MODES:
                if (model_id, input_id, shot) in done:
                    continue
                messages = [{"role": "system", "content": team.SYSTEM_INSTRUCTION},
                            {"role": "user", "content": team.build_user_prompt(text, shot)}]
                options = {"enable_thinking": False} if model_id == "Qwen/Qwen3-0.6B" else {}
                prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, **options)
                encoded = tokenizer(prompt, return_tensors="pt")
                start = time.perf_counter()
                with torch.inference_mode():
                    generated = model.generate(**encoded, max_new_tokens=220, do_sample=False,
                                               pad_token_id=tokenizer.pad_token_id)
                seconds = time.perf_counter() - start
                new_tokens = generated[0, encoded["input_ids"].shape[1]:]
                raw = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
                try:
                    errors = team.validate_payload(team.extract_json(raw))
                except (ValueError, TypeError, json.JSONDecodeError) as exc:
                    errors = [str(exc)]
                rows.append({"model_id": model_id, "input_id": input_id, "shot_mode": shot,
                    "load_seconds": round(load_seconds, 3), "generation_seconds": round(seconds, 3),
                    "output_tokens": len(new_tokens), "schema_valid": not errors,
                    "validation_errors": " | ".join(errors), "raw_output": raw,
                    "quality_score_0_to_10": "", "review_notes": "Pending raw-output review using the shared 10-point rubric."})
                with OUT.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=team.CSV_FIELDS)
                    writer.writeheader()
                    writer.writerows(rows)
                print(f"{model_id} {input_id}/{shot}: {seconds:.3f}s, valid={not errors}", flush=True)
        del model, tokenizer
        gc.collect()
    print(f"Saved {len(rows)} actual generations to {OUT}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-only", action="store_true")
    args = parser.parse_args()
    if args.download_only:
        download_models()
    else:
        run()
