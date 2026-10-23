"""Apply the documented A7 self-evaluation rubric to generated outputs."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from a7.benchmark_contract import PROMPTS
from a7.benchmark_runner import RESULT_COLUMNS


EXPECTED_LABELS = {
    "classification-01": "SHOPPING",
    "classification-02": "MAINTENANCE",
    "classification-03": "APPOINTMENT",
    "classification-04": "DEADLINE",
    "classification-05": "CHORE",
    "priority-01": "HIGH",
    "priority-02": "LOW",
    "priority-03": "HIGH",
    "priority-04": "URGENT",
    "priority-05": "MEDIUM",
}

EXPECTED_CONCEPTS = {
    "extraction-01": [("clean", "kitchen"), ("buy", "snack"), ("fix", "tap")],
    "extraction-02": [("dentist",), ("smoke", "batter"), ("library", "book"), ("guest", "sheet")],
    "extraction-03": [("vacuum",), ("cake",), ("stair", "rail")],
    "extraction-04": [("electricity", "bill"), ("vet",), ("detergent",)],
    "extraction-05": [("refrigerator", "noise"), ("closet",), ("tax", "document")],
    "summary-01": [("old", "food"), ("shelf",), ("organiz",)],
    "summary-02": [("clinic",), ("after 3",), ("calendar",)],
    "summary-03": [("three", "month"), ("provider",), ("increase",)],
    "summary-04": [("book",), ("due",), ("weekend",)],
    "summary-05": [("sheet",), ("towel",), ("bin",), ("lamp",)],
    "planning-01": [("clean",), ("bed", "linen", "sleep"), ("toiletr", "towel", "suppl")],
    "planning-02": [("list", "meal"), ("price", "sale", "budget"), ("90", "cost", "total")],
    "planning-03": [("suppl", "prepare"), ("surface", "counter"), ("floor", "mop"), ("safe", "sanit")],
    "planning-04": [("declutter", "sort"), ("pack",), ("label",), ("move", "date", "transport")],
    "planning-05": [("light",), ("unplug", "device"), ("thermostat", "heat", "cool"), ("monitor", "usage")],
}


def _json_value(output: str):
    text = output.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _concept_coverage(prompt_id: str, output: str) -> tuple[int, int]:
    lowered = output.lower()
    concepts = EXPECTED_CONCEPTS[prompt_id]
    matched = sum(any(term in lowered for term in alternatives) for alternatives in concepts)
    return matched, len(concepts)


def _is_repetitive(output: str) -> bool:
    words = re.findall(r"[a-z]+", output.lower())
    if len(words) < 12:
        return False
    unique_ratio = len(set(words)) / len(words)
    return unique_ratio < 0.22


def review_output(prompt_id: str, output: str) -> dict[str, int | str]:
    """Score one output conservatively using the shared ten-point rubric."""
    prompt_type = next(item["prompt_type"] for item in PROMPTS if item["prompt_id"] == prompt_id)
    text = output.strip()
    parsed = _json_value(text)
    accuracy = adherence = completeness = clarity = supported = 0
    notes: list[str] = []

    if prompt_type in {"classification", "priority_prediction"}:
        expected = EXPECTED_LABELS[prompt_id]
        exact = text.upper().rstrip(".") == expected
        first_label = re.match(r"^([A-Z]+)", text.upper())
        correct = bool(first_label and first_label.group(1) == expected)
        accuracy = 3 if correct else 0
        adherence = 2 if exact else (1 if correct else 0)
        completeness = 2 if correct else 0
        clarity = 2 if exact else (1 if correct else 0)
        supported = 1 if correct else 0
        result = "exactly matched" if exact else "correct label with extra text" if correct else "did not match"
        notes.append(f"Expected exact label {expected}; {result}.")
    else:
        matched, total = _concept_coverage(prompt_id, text)
        ratio = matched / total
        accuracy = 3 if ratio >= 0.8 else 2 if ratio >= 0.5 else 1 if matched else 0
        completeness = 2 if ratio == 1 else 1 if matched else 0

        if prompt_type == "structured_extraction":
            valid = isinstance(parsed, dict) and isinstance(parsed.get("tasks"), list)
            expected_count = len(EXPECTED_CONCEPTS[prompt_id])
            schema_ok = valid and len(parsed["tasks"]) == expected_count and all(
                isinstance(task, dict)
                and {"title", "task_type", "priority", "description"} <= set(task)
                for task in parsed["tasks"]
            )
            adherence = 2 if schema_ok else 0
            notes.append(f"Covered {matched}/{total} concerns; JSON task schema {'valid' if schema_ok else 'invalid'}.")
        elif prompt_type == "summarization":
            schema_ok = isinstance(parsed, dict) and set(parsed) == {"title", "summary"}
            adherence = 2 if schema_ok else 0
            notes.append(f"Covered {matched}/{total} details; summary JSON {'valid' if schema_ok else 'invalid'}.")
        else:
            steps = parsed.get("steps") if isinstance(parsed, dict) else None
            schema_ok = isinstance(steps, list) and 3 <= len(steps) <= 5 and all(isinstance(step, str) for step in steps)
            adherence = 2 if schema_ok else 0
            notes.append(f"Covered {matched}/{total} planning concepts; 3–5 step JSON {'valid' if schema_ok else 'invalid'}.")

        repetitive = _is_repetitive(text)
        clarity = 2 if schema_ok and not repetitive else 1 if text and matched and not repetitive else 0
        unsupported_markers = (
            "i have completed", "i have successfully", "confirmed appointment",
            "next wednesday", "i will send", "your dietary",
        )
        invented = any(marker in text.lower() for marker in unsupported_markers)
        supported = 0 if invented else (1 if matched else 0)
        if repetitive:
            notes.append("Output is repetitive.")
        if invented:
            notes.append("Output adds an unsupported completion claim or specific detail.")

    total_score = accuracy + adherence + completeness + clarity + supported
    return {
        "task_accuracy_0_to_3": accuracy,
        "instruction_adherence_0_to_2": adherence,
        "completeness_0_to_2": completeness,
        "clarity_0_to_2": clarity,
        "no_unsupported_details_0_to_1": supported,
        "self_evaluation_score_1_to_10": max(1, total_score),
        "review_notes": " ".join(notes),
    }


def review_csv(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        if row["status"] == "ok":
            row.update(review_output(row["prompt_id"], row["generated_output"]))
        else:
            row.update({
                "task_accuracy_0_to_3": 0,
                "instruction_adherence_0_to_2": 0,
                "completeness_0_to_2": 0,
                "clarity_0_to_2": 0,
                "no_unsupported_details_0_to_1": 0,
                "self_evaluation_score_1_to_10": 1,
                "review_notes": f"Generation failed: {row['error']}",
            })
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    review_csv(args.path)
    print(f"Reviewed {args.path}")


if __name__ == "__main__":
    main()
