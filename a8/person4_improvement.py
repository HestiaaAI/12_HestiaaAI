"""Reproduce the Person 4 top-k improvement for large/full/hybrid/Q1.

Baseline top-3 already covers the kitchen-close facts, but rank 3
(hybrid-maintenance-03) pulls the generator into inventing a service call.
Intervention: same frozen generator/prompt/decoding/corpus; truncate the
ranked hit list to top-k=2.

Saved evidence: results/person4/improvement_topk2_large_hybrid_Q1.json

  python -m a8.person4_improvement           # validate saved artifact
  python -m a8.person4_improvement --rerun   # regenerate after answer (downloads Qwen)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASE_ID = "large/full/hybrid/Q1"
BASELINE = ROOT / "results" / "person3" / "large" / "rows.jsonl"
ARTIFACT = ROOT / "results" / "person4" / "improvement_topk2_large_hybrid_Q1.json"


def load_baseline():
    for line in BASELINE.open():
        row = json.loads(line)
        if row.get("row_id") == CASE_ID or (
            row.get("query_id") == "Q1" and row.get("strategy") == "hybrid"
        ):
            hits = row.get("retrieved_chunks") or row.get("hits")
            if isinstance(hits, str):
                hits = json.loads(hits)
            return row, hits
    raise SystemExit(f"baseline row {CASE_ID} not found in {BASELINE}")


def validate_artifact():
    data = json.loads(ARTIFACT.read_text())
    assert data["case_id"] == CASE_ID
    assert data["before"]["top_k"] == 3
    assert data["after"]["top_k"] == 2
    assert data["after"]["removed_distractor"]["chunk_id"] == "hybrid-maintenance-03"
    assert data["before"]["answer_quality"] == 0.0
    assert data["after"]["answer_quality"] == 33.33
    assert "service technician" in data["before"]["answer"].lower() or "maintenance" in data["before"]["answer"].lower()
    assert "service technician" not in data["after"]["answer"].lower()
    print(f"OK: {ARTIFACT.relative_to(ROOT.parent)}")
    print(f"  before quality={data['before']['answer_quality']} hits={data['before']['hit_ids']}")
    print(f"  after  quality={data['after']['answer_quality']} hits={data['after']['hit_ids']}")
    return data


def rerun():
    from a8.generation import generate_answer

    row, hits = load_baseline()
    top2 = hits[:2]
    result = generate_answer(row["query"], top2)
    print("query:", row["query"])
    print("top-2:", [h["chunk_id"] for h in top2])
    print("answer:", result["answer"])
    print("generation_ms:", round(result["generation_ms"], 1))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rerun", action="store_true", help="Call the frozen generator on top-2 hits")
    args = parser.parse_args()
    if not ARTIFACT.exists():
        raise SystemExit(f"missing artifact {ARTIFACT}")
    validate_artifact()
    if args.rerun:
        rerun()


if __name__ == "__main__":
    main()
