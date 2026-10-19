"""Summarize measured CSV values; does not manufacture evaluations."""
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
import math

ROOT = Path(__file__).resolve().parents[2]
with (ROOT / "a6_results/person4_benchmark_results.csv").open(encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))
assert len(rows) == 24 and len({(r["model_id"], r["input_id"], r["shot_mode"]) for r in rows}) == 24
assert all(r["quality_score_0_to_10"] for r in rows)
groups = defaultdict(list)
for row in rows:
    groups[row["model_id"]].append(row)
lines = ["# P4 measured benchmark findings", "", "Completed October 18, 2026 on CPU FP32, four PyTorch threads, approximately 15.5 GiB RAM.",
    "Three distinct additional models × two fixed inputs × four shot modes = **24 real generations**.", "",
    "| Model | Runs | Schema valid | Mean generation | Mean reviewed quality /10 |",
    "| --- | ---: | ---: | ---: | ---: |"]
for model, group in groups.items():
    assert len(group) == 8
    valid = sum(r["schema_valid"] == "True" for r in group)
    lines.append(f"| {model} | 8 | {valid}/8 | {mean(float(r['generation_seconds']) for r in group):.3f} s | {mean(float(r['quality_score_0_to_10']) for r in group):.3f} |")
lines += ["", "## Prompting comparison", "", "| Model | Mode | Schema valid | Mean quality /10 |", "| --- | --- | ---: | ---: |"]
for model, group in groups.items():
    for shot in ("zero", "one", "few", "many"):
        subset = [r for r in group if r["shot_mode"] == shot]
        lines.append(f"| {model} | {shot} | {sum(r['schema_valid'] == 'True' for r in subset)}/2 | {mean(float(r['quality_score_0_to_10']) for r in subset):.2f} |")
lines += ["", "## What the outputs show", "",
    "- **Qwen2-0.5B-Instruct:** often recognizes the stated responsibilities but invents invalid task types (CLEANING, PERFORM, RECYCLING) or unsupported detail. Its one schema-valid run still needs type/priority edits; extra urgency keys pass the shared automatic validator but are dropped by the UI.",
    "- **SmolLM-360M-Instruct:** all eight responses return incomplete Python implementation code rather than an input-specific task JSON payload. Several copy prompt examples. This older SmolLM checkpoint is distinct from P1's SmolLM2 checkpoint; do not combine their results under one name.",
    "- **Qwen3-0.6B:** schema reliability alone is misleading: its BD1 zero-shot response uses category names as titles/descriptions instead of actual responsibilities. Other outputs merge or duplicate concerns and overstate urgency. More examples are not a guarantee of better extraction.",
    "", "No P4 candidate is validated as a production-quality extractor from this small test. Keep mandatory editing/confirmation and retry behavior. Person 2's configured default is preserved; selecting a final team winner requires the full team's results and a broader evaluation.",
    "", "## Scoring and reproducibility", "",
    "Each raw response was read and assigned extraction/type/priority/clarity/format points (3/2/2/2/1) in `review_results.py`. CSV notes contain the point breakdown and response-specific reason. These are explicitly **assistant-assisted reviews**, not a blinded human evaluation. The submitter should verify or revise them before submission. The shared automatic schema validator allows extra fields and does not measure relevance.",
    "", "Model revisions, runtime versions, precision and options are in `a6_results/person4_environment.json`. Downloads are excluded from model-load timings. Greedy generation is capped at 220 tokens; Qwen3 thinking is disabled. CPU timings from this machine cannot establish speed differences versus teammates' hardware.",
    "", "## Scaling illustration using measured generation time", "",
    "At 20,000 requests/day, average arrival rate is 0.2315/s. The following is a serialized-worker lower-bound illustration, **not a measured production capacity claim**. Each benchmark worker uses four CPU threads; multiple workers introduce contention and extra model memory.", "",
    "| Model | Mean generation | Busy workers at average load, rounded up | At 5× peak, rounded up |",
    "| --- | ---: | ---: | ---: |"]
for model, group in groups.items():
    latency = mean(float(r["generation_seconds"]) for r in group)
    lines.append(f"| {model} | {latency:.3f} s | {math.ceil(20000 / 86400 * latency)} | {math.ceil(5 * 20000 / 86400 * latency)} |")
lines += ["", "See `local-vs-api.md` for sourced token/rental costs and the distinction between billing break-even and serving capacity.",
    "", "## Team handoff / category limitation", "",
    "P1 can merge `a6_results/person4_benchmark_results.csv` using the existing notebook CSV merge cell. The root P1 notebook is unchanged. P4's executed notebook is `llm-test/ai_prototype.ipynb`.",
    "", "These three models were chosen under the user's instruction to use any models not completed by teammates, constrained by this machine. They do not fill the original missing 7–14B/very-large categories. The original roster has category counts 4/3/3/3/2; the assignment requires 3/3/3/3/3. P1/the team must reconcile the final model list and run the missing categories. P4's additional tests do not imply the complete group 15-model requirement is satisfied.", ""]
path = ROOT / "docs/a6-person-4/benchmark_summary.md"
path.write_text("\n".join(lines), encoding="utf-8")
print(path)
