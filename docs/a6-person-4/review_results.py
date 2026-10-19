"""Apply explicit, assistant-assisted reviews after reading each raw response.

These are content judgments, not heuristic/lexical-overlap scores. The submitter
should inspect the notebook's complete outputs and approve or revise the scores.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "a6_results/person4_benchmark_results.csv"

# Points: extraction /3, types /2, priority /2, clarity /2, format /1.
REVIEWS = {
    ("Qwen/Qwen2-0.5B-Instruct", "BD1", "zero"): ((2, 1, 1, 1, 0), "Found the three concerns but invented additional chores; CLEANING is invalid, adds urgency keys, and understates guest preparation."),
    ("Qwen/Qwen2-0.5B-Instruct", "BD1", "one"): ((3, 0, 0, 1, 0), "Found three tasks; CLOTHES/DIY are invalid types, preparation priorities are weak, and screwdriver repair advice is unsupported."),
    ("Qwen/Qwen2-0.5B-Instruct", "BD1", "few"): ((2, 0, 0, 1, 0), "Recognized three concerns but grocery description becomes cooking; all types invalid and all priorities LOW despite guests tomorrow."),
    ("Qwen/Qwen2-0.5B-Instruct", "BD1", "many"): ((3, 1, 0, 2, 1), "Three clear tasks and valid required-field values; kitchen should be CHORE and preparation priorities are too low. Shared validator allows extra urgency key."),
    ("Qwen/Qwen2-0.5B-Instruct", "BD2", "zero"): ((2, 0, 1, 1, 0), "Four concerns recognized, but replaces detectors rather than batteries; pipe-separated placeholder types invalid and Friday deadline omitted."),
    ("Qwen/Qwen2-0.5B-Instruct", "BD2", "one"): ((3, 0, 1, 2, 0), "Extracted all four actions clearly; PERFORM is invalid, dentist is misclassified CHORE, and Friday deadline is absent."),
    ("Qwen/Qwen2-0.5B-Instruct", "BD2", "few"): ((3, 1, 1, 2, 0), "Four actions preserved; BOOKING/RETURN are invalid, sheets misclassified MAINTENANCE, and safety/deadline priorities need review."),
    ("Qwen/Qwen2-0.5B-Instruct", "BD2", "many"): ((2, 1, 1, 1, 0), "Four titles but book description incorrectly says return to original state; batteries misclassified APPOINTMENT and RECYCLING invalid."),
    ("HuggingFaceTB/SmolLM-360M-Instruct", "BD1", "zero"): ((0, 0, 0, 0, 0), "Returned truncated Python implementation with schema placeholder enums, not an extracted task payload."),
    ("HuggingFaceTB/SmolLM-360M-Instruct", "BD1", "one"): ((0, 0, 0, 0, 0), "Returned truncated Python code copying trash/milk examples rather than usable household task JSON."),
    ("HuggingFaceTB/SmolLM-360M-Instruct", "BD1", "few"): ((0, 0, 0, 0, 0), "Returned recursively nested Python message/entities code, not any input-specific task output."),
    ("HuggingFaceTB/SmolLM-360M-Instruct", "BD1", "many"): ((0, 0, 0, 0, 0), "Returned incomplete Python conversion code, incorrectly treating priorities as task types; no extracted tasks."),
    ("HuggingFaceTB/SmolLM-360M-Instruct", "BD2", "zero"): ((0, 0, 0, 0, 0), "Returned truncated Python splitting pipe-separated strings, not tasks from the natural-language input."),
    ("HuggingFaceTB/SmolLM-360M-Instruct", "BD2", "one"): ((0, 0, 0, 0, 0), "Returned Python example-matching code; book described as a purchase, and no complete task payload."),
    ("HuggingFaceTB/SmolLM-360M-Instruct", "BD2", "few"): ((0, 0, 0, 0, 0), "Returned truncated Python copying trash/milk/gas/light-bulb examples unrelated to this input."),
    ("HuggingFaceTB/SmolLM-360M-Instruct", "BD2", "many"): ((0, 0, 0, 0, 0), "Returned truncated pipe-splitting Python implementation instead of input-specific JSON tasks."),
    ("Qwen/Qwen3-0.6B", "BD1", "zero"): ((0, 0, 0, 0, 1), "Schema-valid but titles/descriptions are category names; invents appointment/deadline and fails actual household extraction."),
    ("Qwen/Qwen3-0.6B", "BD1", "one"): ((2, 2, 1, 1, 1), "Kitchen and groceries are relevant, but tap repair is merged into kitchen description rather than a separate task; grocery urgency understated."),
    ("Qwen/Qwen3-0.6B", "BD1", "few"): ((2, 2, 0, 2, 1), "Extracted three concerns but invents an arrival-scheduling task; preparation is only MEDIUM while the tap is URGENT without an immediate safety basis."),
    ("Qwen/Qwen3-0.6B", "BD1", "many"): ((2, 2, 0, 2, 1), "Extracted concerns but duplicates kitchen work as vacuuming/cleaning; preparation priorities too low and tap urgency not justified by safety evidence."),
    ("Qwen/Qwen3-0.6B", "BD2", "zero"): ((3, 1, 1, 2, 0), "Extracted all four concerns and Friday deadline clearly; three task types are invalid CHORE|APPOINTMENT composites and dentist priority is inflated."),
    ("Qwen/Qwen3-0.6B", "BD2", "one"): ((3, 2, 1, 2, 1), "Four distinct, clear tasks and appropriate types; dentist HIGH is unsupported and Friday URGENT assumes an unknown current day."),
    ("Qwen/Qwen3-0.6B", "BD2", "few"): ((3, 1, 0, 2, 1), "Four concerns extracted clearly, but replacing batteries is SHOPPING; dentist HIGH, batteries LOW and Friday URGENT need correction."),
    ("Qwen/Qwen3-0.6B", "BD2", "many"): ((2, 1, 1, 1, 1), "Changes washing sheets to vacuuming; batteries SHOPPING and library return CHORE are poor types, with no Friday deadline in description."),
}


def apply_reviews():
    with CSV.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    assert len(rows) == 24, "Wait for all 24 actual generations before scoring"
    for row in rows:
        key = row["model_id"], row["input_id"], row["shot_mode"]
        points, note = REVIEWS[key]
        assert all(0 <= value <= limit for value, limit in zip(points, (3, 2, 2, 2, 1)))
        row["quality_score_0_to_10"] = sum(points)
        row["review_notes"] = "Assistant-assisted review; E/T/P/C/F=" + "/".join(map(str, points)) + ". " + note
    with CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print("Reviewed", len(rows), "raw responses; submitter review remains recommended.")


if __name__ == "__main__":
    apply_reviews()
