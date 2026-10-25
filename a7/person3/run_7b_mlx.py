"""Finish the Qwen2.5-7B benchmark rows on a 16 GB Mac.

Full float16 does not fit in memory, and a disk-offload run produced about
one prompt every 25 minutes. These rows use the 4-bit MLX conversion of the
same instruct model, greedy decoding, and the shared prompt text. The CSV
keeps the registry model id. See person3_benchmark_environment.json.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from mlx_lm import load, stream_generate
from mlx_lm.sample_utils import make_sampler

from a7.benchmark_contract import PROMPTS, render_prompt
from a7.benchmark_runner import _empty_review_fields, _read_rows, _write_rows, select_models

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MLX_REPO = "mlx-community/Qwen2.5-7B-Instruct-4bit"
OUTPUT = Path("a7/results/person3_benchmark.csv")
MAX_NEW_TOKENS = 220
DEVICE_LABEL = "mlx-4bit"


def prompt_ids(tokenizer, prompt_text: str) -> list[int]:
    messages = [{"role": "user", "content": prompt_text}]
    try:
        ids = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, enable_thinking=False,
        )
    except TypeError:
        ids = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
    if hasattr(ids, "ids"):
        ids = ids.ids
    if hasattr(ids, "tolist"):
        ids = ids.tolist()
    return list(ids)


def main() -> None:
    model_info = select_models(model_ids=[MODEL_ID])[0]
    rows = [
        row for row in _read_rows(OUTPUT)
        if row.get("status") == "ok" and not (
            row["model_id"] == MODEL_ID and row.get("device") != DEVICE_LABEL
        )
    ]
    completed = {(row["model_id"], row["prompt_id"]) for row in rows}
    remaining = [prompt for prompt in PROMPTS if (MODEL_ID, prompt["prompt_id"]) not in completed]
    print(f"kept {len(rows)} remaining {len(remaining)}", flush=True)
    if not remaining:
        _write_rows(OUTPUT, rows)
        print(f"Saved {len(rows)} rows to {OUTPUT}")
        return

    model, tokenizer = load(MLX_REPO)
    sampler = make_sampler(temp=0.0)

    for prompt in remaining:
        prompt_text = render_prompt(prompt)
        ids = prompt_ids(tokenizer, prompt_text)
        started = time.perf_counter()
        text = ""
        last = None
        for response in stream_generate(
            model, tokenizer, ids, max_tokens=MAX_NEW_TOKENS, sampler=sampler,
        ):
            text += response.text
            last = response
        latency = time.perf_counter() - started
        output_tokens = int(last.generation_tokens) if last is not None else 0
        rows.append({
            "model_id": MODEL_ID,
            "model_category": model_info["category"],
            "owner": model_info["owner"],
            "prompt_id": prompt["prompt_id"],
            "prompt_type": prompt["prompt_type"],
            "prompt": prompt["input"],
            "latency_seconds": round(latency, 4),
            "output_tokens": output_tokens,
            "tokens_per_second": round(output_tokens / latency, 4) if latency else "",
            "generated_output": text.strip(),
            "status": "ok",
            "error": "",
            "device": DEVICE_LABEL,
            "max_new_tokens": MAX_NEW_TOKENS,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            **_empty_review_fields(),
        })
        _write_rows(OUTPUT, rows)
        print(f"{prompt['prompt_id']} {output_tokens} tok {latency:.1f}s", flush=True)

    print(f"Saved {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
