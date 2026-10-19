#!/usr/bin/env python3
"""Person 2 benchmarks using Shivani's PR #25 shared contract (exact prompts/CSV).

Produces: a6_results/person2_benchmark_results.csv

  export HF_HOME="$PWD/.cache/huggingface"
  python docs/a6-person-2/run_shivani_contract_benchmark.py
"""

from __future__ import annotations

import csv
import gc
import json
import re
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "a6_results" / "person2_benchmark_results.csv"

PERSON_2_MODELS = [
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "Qwen/Qwen2.5-1.5B-Instruct",
    "HuggingFaceTB/SmolLM2-1.7B-Instruct",
    "Qwen/Qwen2.5-3B-Instruct",
]

TASK_TYPES = {"CHORE", "APPOINTMENT", "DEADLINE", "ERRAND", "MAINTENANCE", "SHOPPING", "OTHER"}
PRIORITIES = {"LOW", "MEDIUM", "HIGH", "URGENT"}
REQUIRED_FIELDS = {"title", "task_type", "priority", "description"}

SYSTEM_INSTRUCTION = """You are Hestia's household task extraction assistant.
Convert the user's message into separate household tasks.
Return JSON only in this exact shape:
{"tasks":[{"title":"...","task_type":"CHORE|APPOINTMENT|DEADLINE|ERRAND|MAINTENANCE|SHOPPING|OTHER","priority":"LOW|MEDIUM|HIGH|URGENT","description":"..."}]}
Do not invent concerns that the user did not mention. Use URGENT only for an immediate safety risk or a deadline within 24 hours. Keep titles and descriptions concise."""

TEST_INPUTS = {
    "BD1": "Guests are coming tomorrow. The kitchen is messy, we need groceries, and the bathroom tap is leaking badly.",
    "BD2": "This week I need to book the dentist, replace the smoke detector batteries, return a library book by Friday, and wash the guest-room sheets.",
}

EXAMPLES = [
    {
        "input": "The trash is full and we are out of milk.",
        "output": {"tasks": [
            {"title": "Take out the trash", "task_type": "CHORE", "priority": "MEDIUM", "description": "Empty the full household trash bin."},
            {"title": "Buy milk", "task_type": "SHOPPING", "priority": "MEDIUM", "description": "Purchase milk for the household."},
        ]},
    },
    {
        "input": "The gas stove smells like gas, and the hallway light bulb needs replacing.",
        "output": {"tasks": [
            {"title": "Check gas leak", "task_type": "MAINTENANCE", "priority": "URGENT", "description": "Stop using the stove and arrange an immediate gas safety inspection."},
            {"title": "Replace hallway light bulb", "task_type": "MAINTENANCE", "priority": "LOW", "description": "Replace the burned-out hallway light bulb."},
        ]},
    },
    {
        "input": "The dog needs a vet appointment and the living room needs vacuuming.",
        "output": {"tasks": [
            {"title": "Book vet appointment", "task_type": "APPOINTMENT", "priority": "MEDIUM", "description": "Schedule a veterinary appointment for the dog."},
            {"title": "Vacuum living room", "task_type": "CHORE", "priority": "LOW", "description": "Vacuum the living-room floor."},
        ]},
    },
]

SHOT_MODES = ["zero", "one", "few", "many"]
CSV_FIELDS = [
    "model_id", "input_id", "shot_mode", "load_seconds", "generation_seconds",
    "output_tokens", "schema_valid", "validation_errors", "raw_output",
    "quality_score_0_to_10", "review_notes",
]


def build_user_prompt(text, shot_mode):
    shot_counts = {"zero": 0, "one": 1, "few": 2, "many": 3}
    examples = EXAMPLES[: shot_counts[shot_mode]]
    example_text = "\n\n".join(
        f"Example input: {item['input']}\nExample output: {json.dumps(item['output'])}"
        for item in examples
    )
    prefix = f"{example_text}\n\n" if example_text else ""
    return f"{prefix}Household message: {text}\nJSON output:"


def extract_json(text):
    def reject_duplicate_keys(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"Duplicate JSON key: {key}")
            value[key] = item
        return value

    decoder = json.JSONDecoder(object_pairs_hook=reject_duplicate_keys)
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
            return value
        except json.JSONDecodeError:
            continue
    raise ValueError("No valid JSON object found")


def validate_payload(payload):
    errors = []
    if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
        return ["Root must be an object containing a tasks list"]
    if not payload["tasks"]:
        errors.append("tasks must not be empty")
    for index, task in enumerate(payload["tasks"], start=1):
        if not isinstance(task, dict):
            errors.append(f"Task {index} is not an object")
            continue
        missing = REQUIRED_FIELDS - task.keys()
        if missing:
            errors.append(f"Task {index} missing: {sorted(missing)}")
        if task.get("task_type") not in TASK_TYPES:
            errors.append(f"Task {index} has invalid task_type")
        if task.get("priority") not in PRIORITIES:
            errors.append(f"Task {index} has invalid priority")
        if not str(task.get("title", "")).strip():
            errors.append(f"Task {index} has an empty title")
        if not str(task.get("description", "")).strip():
            errors.append(f"Task {index} has an empty description")
    return errors


def format_for_model(tokenizer, user_prompt):
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": user_prompt},
    ]
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return f"Instruction:\n{SYSTEM_INSTRUCTION}\n\nUser:\n{user_prompt}\n\nAssistant:\n"


def provisional_quality(schema_valid: bool, payload, brain_dump: str) -> tuple[int | None, str]:
    """Lightweight review placeholder; replace with manual scores before final submit if needed."""
    if not schema_valid or not payload:
        return 0, "Schema invalid or unparseable."
    titles = " ".join(t.get("title", "") for t in payload["tasks"]).lower()
    # crude overlap with dump words
    hits = sum(1 for w in re.findall(r"[a-z]{4,}", brain_dump.lower()) if w in titles)
    n = len(payload["tasks"])
    if n >= 3 and hits >= 2:
        return 7, "Provisional: schema OK, multiple tasks, some lexical overlap with dump."
    if n >= 2 and hits >= 1:
        return 5, "Provisional: schema OK, partial coverage."
    return 3, "Provisional: schema OK but weak relevance; review manually."


def benchmark_model(model_id, device, dtype):
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype)
    model.to(device)
    model.eval()
    load_seconds = time.perf_counter() - started
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    rows = []
    for input_id, brain_dump in TEST_INPUTS.items():
        for shot_mode in SHOT_MODES:
            prompt = format_for_model(tokenizer, build_user_prompt(brain_dump, shot_mode))
            encoded = tokenizer(prompt, return_tensors="pt").to(device)
            generation_started = time.perf_counter()
            with torch.inference_mode():
                generated = model.generate(
                    **encoded,
                    max_new_tokens=220,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                )
            generation_seconds = time.perf_counter() - generation_started
            new_tokens = generated[0, encoded["input_ids"].shape[1] :]
            raw_output = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
            payload = None
            try:
                payload = extract_json(raw_output)
                validation_errors = validate_payload(payload)
            except (ValueError, json.JSONDecodeError) as exc:
                validation_errors = [str(exc)]
            schema_valid = not validation_errors
            score, notes = provisional_quality(schema_valid, payload, brain_dump)
            rows.append({
                "model_id": model_id,
                "input_id": input_id,
                "shot_mode": shot_mode,
                "load_seconds": round(load_seconds, 3),
                "generation_seconds": round(generation_seconds, 3),
                "output_tokens": int(new_tokens.shape[-1]),
                "schema_valid": schema_valid,
                "validation_errors": " | ".join(validation_errors),
                "raw_output": raw_output,
                "quality_score_0_to_10": score,
                "review_notes": notes,
            })
            print(f"  {input_id}/{shot_mode} valid={schema_valid} score={score}", flush=True)

    del model, tokenizer
    gc.collect()
    if device == "mps":
        torch.mps.empty_cache()
    elif device == "cuda":
        torch.cuda.empty_cache()
    return rows


def main():
    device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device in {"mps", "cuda"} else torch.float32
    print("Device:", device)
    all_rows = []
    for model_id in PERSON_2_MODELS:
        print(f"Benchmarking {model_id}...", flush=True)
        try:
            all_rows.extend(benchmark_model(model_id, device, dtype))
        except Exception as exc:
            all_rows.append({
                "model_id": model_id,
                "input_id": "MODEL_LOAD",
                "shot_mode": "n/a",
                "load_seconds": None,
                "generation_seconds": None,
                "output_tokens": None,
                "schema_valid": False,
                "validation_errors": f"{type(exc).__name__}: {exc}",
                "raw_output": "",
                "quality_score_0_to_10": None,
                "review_notes": "Model could not be benchmarked; retain the error as evidence.",
            })
            print("  ERROR", exc, flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Wrote {OUT} ({len(all_rows)} rows)")


if __name__ == "__main__":
    main()
