"""Run the shared Assignment 7 prompt matrix against selected local models."""

from __future__ import annotations

import argparse
import csv
import gc
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from a7.benchmark_contract import MODEL_REGISTRY, PROMPTS, render_prompt, validate_contract


RESULT_COLUMNS = [
    "model_id",
    "model_category",
    "owner",
    "prompt_id",
    "prompt_type",
    "prompt",
    "latency_seconds",
    "output_tokens",
    "tokens_per_second",
    "generated_output",
    "status",
    "error",
    "device",
    "max_new_tokens",
    "generated_at_utc",
    "task_accuracy_0_to_3",
    "instruction_adherence_0_to_2",
    "completeness_0_to_2",
    "clarity_0_to_2",
    "no_unsupported_details_0_to_1",
    "self_evaluation_score_1_to_10",
    "review_notes",
]


def select_models(owner: str | None = None, model_ids: Iterable[str] | None = None) -> list[dict]:
    """Return roster entries for one owner or an explicit list of model IDs."""
    known = {model["model_id"]: model for model in MODEL_REGISTRY}
    if model_ids:
        requested = list(model_ids)
        unknown = [model_id for model_id in requested if model_id not in known]
        if unknown:
            raise ValueError(f"Unknown model ID(s): {', '.join(unknown)}")
        return [known[model_id] for model_id in requested]
    if owner:
        selected = [model for model in MODEL_REGISTRY if model["owner"] == owner]
        if not selected:
            raise ValueError(f"Unknown owner: {owner}")
        return selected
    return list(MODEL_REGISTRY)


def expected_keys(models: Iterable[dict], prompts: Iterable[dict]) -> list[tuple[str, str]]:
    return [(model["model_id"], prompt["prompt_id"]) for model in models for prompt in prompts]


def validate_result_rows(rows: list[dict], models: list[dict], prompts: list[dict]) -> None:
    """Validate row schema and exact model/prompt coverage."""
    for row in rows:
        missing = set(RESULT_COLUMNS) - set(row)
        if missing:
            raise ValueError(f"Result row missing columns: {sorted(missing)}")
    keys = [(row["model_id"], row["prompt_id"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate model/prompt result rows found")
    expected = set(expected_keys(models, prompts))
    actual = set(keys)
    if actual != expected:
        raise ValueError(f"Result coverage mismatch: missing={len(expected-actual)}, extra={len(actual-expected)}")


def _read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def _device_name(requested: str, torch) -> str:
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _synchronize(device: str, torch) -> None:
    if device == "cuda":
        torch.cuda.synchronize()
    elif device == "mps":
        torch.mps.synchronize()


def _format_input(tokenizer, prompt_text: str) -> str:
    if getattr(tokenizer, "chat_template", None):
        messages = [{"role": "user", "content": prompt_text}]
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return prompt_text


def _empty_review_fields() -> dict[str, str]:
    return {
        "task_accuracy_0_to_3": "",
        "instruction_adherence_0_to_2": "",
        "completeness_0_to_2": "",
        "clarity_0_to_2": "",
        "no_unsupported_details_0_to_1": "",
        "self_evaluation_score_1_to_10": "",
        "review_notes": "",
    }


def run_matrix(
    models: list[dict],
    output_path: Path,
    device_request: str = "auto",
    dtype_request: str = "auto",
    max_new_tokens: int = 220,
    resume: bool = True,
) -> list[dict]:
    """Generate and checkpoint one output for every selected model/prompt pair."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    validate_contract()
    rows = _read_rows(output_path) if resume else []
    # Failed rows remain visible after a run, but a later resume retries them.
    rows = [row for row in rows if row.get("status") == "ok"]
    completed = {(row["model_id"], row["prompt_id"]) for row in rows}
    device = _device_name(device_request, torch)

    for model_info in models:
        model_id = model_info["model_id"]
        remaining = [prompt for prompt in PROMPTS if (model_id, prompt["prompt_id"]) not in completed]
        if not remaining:
            continue

        tokenizer = model = None
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            if tokenizer.pad_token_id is None:
                tokenizer.pad_token = tokenizer.eos_token
            if dtype_request == "float16":
                dtype = torch.float16
            elif dtype_request == "float32":
                dtype = torch.float32
            else:
                dtype = torch.float16 if device in {"cuda", "mps"} else torch.float32
            model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype, low_cpu_mem_usage=True)
            model.to(device)
            model.eval()

            for prompt in remaining:
                prompt_text = render_prompt(prompt)
                formatted = _format_input(tokenizer, prompt_text)
                inputs = tokenizer(formatted, return_tensors="pt").to(device)
                started = time.perf_counter()
                with torch.inference_mode():
                    output = model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        do_sample=False,
                        pad_token_id=tokenizer.pad_token_id,
                        eos_token_id=tokenizer.eos_token_id,
                    )
                _synchronize(device, torch)
                latency = time.perf_counter() - started
                generated_ids = output[0, inputs["input_ids"].shape[1] :]
                output_tokens = int(generated_ids.shape[0])
                generated = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
                row = {
                    "model_id": model_id,
                    "model_category": model_info["category"],
                    "owner": model_info["owner"],
                    "prompt_id": prompt["prompt_id"],
                    "prompt_type": prompt["prompt_type"],
                    "prompt": prompt["input"],
                    "latency_seconds": round(latency, 4),
                    "output_tokens": output_tokens,
                    "tokens_per_second": round(output_tokens / latency, 4) if latency else "",
                    "generated_output": generated,
                    "status": "ok",
                    "error": "",
                    "device": device,
                    "max_new_tokens": max_new_tokens,
                    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                    **_empty_review_fields(),
                }
                rows.append(row)
                completed.add((model_id, prompt["prompt_id"]))
                _write_rows(output_path, rows)
        except Exception as exc:
            error = f"{type(exc).__name__}: {str(exc)[:500]}"
            for prompt in remaining:
                key = (model_id, prompt["prompt_id"])
                if key in completed:
                    continue
                rows.append(
                    {
                        "model_id": model_id,
                        "model_category": model_info["category"],
                        "owner": model_info["owner"],
                        "prompt_id": prompt["prompt_id"],
                        "prompt_type": prompt["prompt_type"],
                        "prompt": prompt["input"],
                        "latency_seconds": "",
                        "output_tokens": "",
                        "tokens_per_second": "",
                        "generated_output": "",
                        "status": "error",
                        "error": error,
                        "device": device,
                        "max_new_tokens": max_new_tokens,
                        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                        **_empty_review_fields(),
                    }
                )
                completed.add(key)
            _write_rows(output_path, rows)
        finally:
            del model, tokenizer
            gc.collect()
            if device == "cuda":
                torch.cuda.empty_cache()
            elif device == "mps":
                torch.mps.empty_cache()

    validate_result_rows(rows, models, PROMPTS)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--owner", choices=["P1", "P2", "P3", "architecture"], default="P1")
    selection.add_argument("--models", nargs="+")
    parser.add_argument("--output", type=Path, default=Path("a7/results/person1_benchmark.csv"))
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    parser.add_argument("--dtype", choices=["auto", "float16", "float32"], default="auto")
    parser.add_argument("--max-new-tokens", type=int, default=220)
    parser.add_argument("--restart", action="store_true", help="Replace rather than resume an existing output CSV")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    models = select_models(model_ids=args.models) if args.models else select_models(owner=args.owner)
    if args.dry_run:
        print(json.dumps({"models": models, "prompts": len(PROMPTS), "evaluations": len(models) * len(PROMPTS)}, indent=2))
        return
    rows = run_matrix(
        models,
        args.output,
        device_request=args.device,
        dtype_request=args.dtype,
        max_new_tokens=args.max_new_tokens,
        resume=not args.restart,
    )
    print(f"Saved {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
