"""P3 runner for P1's unchanged notebook contract; no Django dependency.

Preflight: python llm-test/person3_benchmark.py --preflight
Real runs: python llm-test/person3_benchmark.py --run
Requires adequate accelerator memory and approved access to gated models.
"""
import argparse
import ast
import csv
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "ai_prototype.ipynb"
CONSTANTS = {"MODEL_ROSTER", "TASK_TYPES", "PRIORITIES", "REQUIRED_FIELDS",
             "SYSTEM_INSTRUCTION", "TEST_INPUTS", "EXAMPLES", "RESULT_COLUMNS"}
SHOT_COUNTS = {"zero": 0, "one": 1, "few": 2, "many": 3}


def load_contract(path=NOTEBOOK):
    """Read literal benchmark constants without executing notebook cells."""
    data = json.loads(path.read_text())
    contract = {}
    for cell in data["cells"]:
        if cell["cell_type"] != "code":
            continue
        for node in ast.parse("".join(cell["source"])).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in CONSTANTS:
                        contract[target.id] = ast.literal_eval(node.value)
    if contract.keys() != CONSTANTS:
        raise ValueError(f"Missing shared constants: {CONSTANTS - contract.keys()}")
    return contract


def build_user_prompt(contract, text, shot_mode):
    examples = contract["EXAMPLES"][:SHOT_COUNTS[shot_mode]]
    example_text = "\n\n".join(
        f"Example input: {item['input']}\nExample output: {json.dumps(item['output'])}"
        for item in examples
    )
    prefix = f"{example_text}\n\n" if example_text else ""
    return f"{prefix}Household message: {text}\nJSON output:"


def extract_json(text):
    # Same first-complete-object parsing policy as P1's notebook.
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    decoder = json.JSONDecoder(object_pairs_hook=reject_duplicates)
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
            return value
        except json.JSONDecodeError:
            continue
    raise ValueError("No valid JSON object found")


def validate_payload(contract, payload):
    # Deliberately mirrors the shared rubric, not the stricter application parser.
    errors = []
    if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
        return ["Root must be an object containing a tasks list"]
    if not payload["tasks"]:
        errors.append("tasks must not be empty")
    for index, task in enumerate(payload["tasks"], start=1):
        if not isinstance(task, dict):
            errors.append(f"Task {index} is not an object")
            continue
        missing = contract["REQUIRED_FIELDS"] - task.keys()
        if missing:
            errors.append(f"Task {index} missing: {sorted(missing)}")
        if task.get("task_type") not in contract["TASK_TYPES"]:
            errors.append(f"Task {index} has invalid task_type")
        if task.get("priority") not in contract["PRIORITIES"]:
            errors.append(f"Task {index} has invalid priority")
        if not str(task.get("title", "")).strip():
            errors.append(f"Task {index} has an empty title")
        if not str(task.get("description", "")).strip():
            errors.append(f"Task {index} has an empty description")
    return errors


def physical_memory_gib():
    if platform.system() == "Darwin":
        return int(subprocess.check_output(["sysctl", "-n", "hw.memsize"])) / 1024**3
    return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024**3


def estimated_memory_gib(params_b, device, precision="native"):
    # FP16 on accelerators and FP32 on CPU, plus conservative load/KV overhead.
    bytes_per_parameter = 0.5 if precision == "nf4" else 4 if device == "cpu" else 2
    overhead_gib = 3 if precision == "nf4" else 2
    return params_b * 1e9 * bytes_per_parameter * 1.4 / 1024**3 + overhead_gib


def model_rows(contract):
    models = [row for row in contract["MODEL_ROSTER"] if row["owner"] == "P3"]
    if len(models) != 4:
        raise ValueError("P1's current contract must assign exactly four models to P3")
    return models


def error_row(contract, model_id, message):
    row = {name: None for name in contract["RESULT_COLUMNS"]}
    row.update(model_id=model_id, input_id="MODEL_LOAD", shot_mode="n/a", schema_valid=False,
               validation_errors=message, raw_output="",
               review_notes="No generation measured. This row is not a completed benchmark.")
    return row


def load_model(model_id, device, precision, compute_dtype="float16"):
    if precision == "nf4" and device != "cuda":
        raise ValueError("NF4 loading in this runner requires a CUDA GPU")
    import torch
    from transformers import AutoModelForCausalLM

    dtype = torch.float32 if compute_dtype == "float32" else torch.float16
    options = {"torch_dtype": torch.float32 if device == "cpu" else dtype,
               "trust_remote_code": False}
    if precision == "nf4":
        from transformers import BitsAndBytesConfig
        options.update(
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=dtype,
            ),
            device_map={"": 0}, low_cpu_mem_usage=True, attn_implementation="eager",
        )
    model = AutoModelForCausalLM.from_pretrained(model_id, **options)
    if precision == "native":
        model.to(device)
    return model


def run_model(contract, model_id, device, precision="native", compute_dtype="float16"):
    import torch
    from transformers import AutoTokenizer

    model = None
    tokenizer = None
    try:
        started = time.perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=False)
        model = load_model(model_id, device, precision, compute_dtype)
        model.eval()
        if device == "cuda":
            torch.cuda.synchronize()
        load_seconds = time.perf_counter() - started
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token_id = tokenizer.eos_token_id
        for input_id, brain_dump in contract["TEST_INPUTS"].items():
            for shot_mode in SHOT_COUNTS:
                user_prompt = build_user_prompt(contract, brain_dump, shot_mode)
                messages = [{"role": "system", "content": contract["SYSTEM_INSTRUCTION"]},
                            {"role": "user", "content": user_prompt}]
                if getattr(tokenizer, "chat_template", None):
                    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                else:
                    prompt = f"Instruction:\n{contract['SYSTEM_INSTRUCTION']}\n\nUser:\n{user_prompt}\n\nAssistant:\n"
                encoded = tokenizer(prompt, return_tensors="pt").to(device)
                if device == "cuda":
                    torch.cuda.synchronize()
                generation_started = time.perf_counter()
                with torch.inference_mode():
                    generated = model.generate(**encoded, max_new_tokens=220, do_sample=False,
                                               pad_token_id=tokenizer.pad_token_id)
                if device == "cuda":
                    torch.cuda.synchronize()
                generation_seconds = time.perf_counter() - generation_started
                new_tokens = generated[0, encoded["input_ids"].shape[1]:]
                raw = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
                try:
                    errors = validate_payload(contract, extract_json(raw))
                except ValueError as exc:
                    errors = [str(exc)]
                yield {
                    "model_id": model_id, "input_id": input_id, "shot_mode": shot_mode,
                    "load_seconds": round(load_seconds, 3),
                    "generation_seconds": round(generation_seconds, 3),
                    "output_tokens": int(new_tokens.shape[-1]), "schema_valid": not errors,
                    "validation_errors": "; ".join(errors), "raw_output": raw,
                    "quality_score_0_to_10": None,
                    "review_notes": f"Precision: {precision}; compute dtype: {compute_dtype}. Not yet reviewed; score manually using P1's rubric.",
                }
    finally:
        del model, tokenizer
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
        elif device == "mps":
            torch.mps.empty_cache()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"])
    parser.add_argument("--precision", choices=["native", "nf4"], default="native",
                        help="nf4 is CUDA-only 4-bit inference; saved separately from native results.")
    parser.add_argument("--nf4-compute-dtype", choices=["float16", "float32"], default="float16",
                        help="NF4 compute and non-quantized module dtype; float32 results are saved separately.")
    parser.add_argument("--model", action="append", help="Optional assigned model ID; may be repeated.")
    args = parser.parse_args()
    if args.precision == "nf4" and args.device in {"cpu", "mps"}:
        parser.error("--precision nf4 requires --device cuda")
    if args.nf4_compute_dtype != "float16" and args.precision != "nf4":
        parser.error("--nf4-compute-dtype requires --precision nf4")
    contract = load_contract()
    models = model_rows(contract)
    if args.model:
        if set(args.model) - {row["model_id"] for row in models}:
            parser.error("--model must be assigned to P3 in the shared notebook")
        models = [row for row in models if row["model_id"] in args.model]

    if args.run:
        import torch
        device = args.device or ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    else:
        device = args.device or ("mps" if platform.system() == "Darwin" and platform.machine() == "arm64" else "cpu")
    if args.precision == "nf4" and device != "cuda":
        parser.error("NF4 requires a CUDA GPU")
    memory = physical_memory_gib()
    if device == "cuda":
        if args.run:
            if not torch.cuda.is_available():
                parser.error("CUDA is unavailable; select a GPU runtime first")
            memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        else:
            parser.error("CUDA preflight needs torch; use --run on the GPU host to measure VRAM.")
    results_dir = ROOT / "a6_results"
    results_dir.mkdir(exist_ok=True)
    filename = "person3_preflight.csv" if args.preflight else "person3_benchmark_results.csv"
    if args.precision == "nf4":
        filename = "person3_nf4_preflight.csv" if args.preflight else "person3_nf4_results.csv"
    if args.precision == "nf4" and args.nf4_compute_dtype == "float32":
        filename = "person3_nf4_fp32_preflight.csv" if args.preflight else "person3_nf4_fp32_results.csv"
    output = results_dir / filename
    if args.precision == "nf4" and args.nf4_compute_dtype == "float32" and output.exists():
        parser.error(f"Refusing to overwrite {output}; preserve or rename it before a new run")
    # --run writes a new result file intentionally; copy reviewed results before rerunning.
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=contract["RESULT_COLUMNS"], lineterminator="\n")
        writer.writeheader()
        for row in models:
            model_id = row["model_id"]
            estimate = estimated_memory_gib(row["params_b"], device, args.precision)
            if args.preflight or estimate > memory:
                message = f"Preflight only: estimated {estimate:.1f} GiB > available device capacity {memory:.1f} GiB." if estimate > memory else "Preflight only: memory check passed; generation not requested."
                if row.get("access") == "gated":
                    message += " HF license/access approval and authenticated downloads are also required."
                writer.writerow(error_row(contract, model_id, message))
                print(model_id, message, flush=True)
            else:
                print("Benchmarking", model_id, flush=True)
                try:
                    for result in run_model(contract, model_id, device, args.precision, args.nf4_compute_dtype):
                        writer.writerow(result)
                        stream.flush()
                        print(result["input_id"], result["shot_mode"], result["generation_seconds"], result["schema_valid"], flush=True)
                except Exception as exc:
                    # Do not dump authentication headers/tokens from dependency exceptions.
                    writer.writerow(error_row(contract, model_id,
                                               f"{type(exc).__name__}: model run failed; check HF access, dependencies and memory. Partial rows, if any, are retained."))
            stream.flush()
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "notebook_sha256": hashlib.sha256(NOTEBOOK.read_bytes()).hexdigest(),
        "python": platform.python_version(), "platform": platform.platform(),
        "device": device, "device_capacity_gib": round(memory, 2),
        "precision": args.precision,
        "max_new_tokens": 220, "do_sample": False, "models": [row["model_id"] for row in models],
        "mode": "preflight_only" if args.preflight else "generation",
    }
    if args.run:
        import transformers
        metadata.update(torch=torch.__version__, transformers=transformers.__version__)
        if args.precision == "nf4":
            import importlib.metadata
            metadata.update(bitsandbytes=importlib.metadata.version("bitsandbytes"),
                            accelerate=importlib.metadata.version("accelerate"),
                            quantization={"bits": 4, "type": "nf4", "double_quant": True,
                                          "compute_dtype": args.nf4_compute_dtype,
                                          "non_quantized_dtype": args.nf4_compute_dtype, "attention": "eager"})
    output.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("Saved", output)


if __name__ == "__main__":
    main()
