"""Rebuild A9's scored comparison from retained HTTP evidence and review notes."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_phase(phase):
    rows = [json.loads(line) for line in (ROOT/"results"/phase/"requests.jsonl").read_text().splitlines()]
    expected = [case["id"] for case in json.loads((ROOT/"inputs.json").read_text())]
    if [row["id"] for row in rows] != expected:
        raise ValueError(f"Incomplete or reordered evaluation: {phase}")
    return rows


def review_fingerprint(row):
    payload = {key: row[key] for key in ("question", "result", "error", "form_errors", "trace")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def export_table():
    with (ROOT/"reviews.csv").open(encoding="utf-8") as file:
        reviews = {(r["phase"], r["id"]): r for r in csv.DictReader(file)}
    expected_cases = {case["id"]: case for case in json.loads((ROOT/"inputs.json").read_text())}
    evaluated = []
    for phase in ("baseline", "overlap"):
        for row in load_phase(phase):
            review = reviews[phase, row["id"]]
            if review["evidence_sha256"] != review_fingerprint(row):
                raise ValueError("Evidence changed since review")
            facts = [int(number) for number in review["matched_facts"].split()]
            expected = expected_cases[row["id"]]
            if "required_facts" in expected:
                fact_count = len(expected["required_facts"])
                if len(set(facts)) != len(facts) or any(n<1 or n>fact_count for n in facts):
                    raise ValueError("Review contains an invalid fact index")
                correctness = round(100 * len(facts) / fact_count, 2)
            else:
                correctness = 100 if review["expected_behavior_met"] == "yes" else 0
            actual = row["error"] or (row["result"] or {}).get("answer") or json.dumps(row["form_errors"])
            evaluated.append({
                "phase": phase, "id": row["id"], "input": row["question"],
                "expected_behavior": row["expected_behavior"], "actual_visible_output": actual,
                "http_status": row["http_status"], "correctness_percent": correctness,
                "expected_behavior_met": review["expected_behavior_met"],
                "usefulness": review["usefulness"], "structure": review["structure"],
                "latency_seconds": round(row["request_seconds"], 3), "notes": review["notes"],
            })
    if set(reviews) != {(r["phase"], r["id"]) for r in evaluated}:
        raise ValueError("Unexpected or missing review")
    with (ROOT/"evaluation.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(evaluated[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(evaluated)
    return evaluated


if __name__ == "__main__":
    for row in export_table():
        print(row["phase"], row["id"], row["correctness_percent"], row["expected_behavior_met"])
