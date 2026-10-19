"""Explicit assistant-assisted judgments after reading all 32 actual outputs.

This is a frozen review of this run, not an automatic scoring algorithm.
The submitter can approve or revise these judgments after inspecting raw output.
"""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "a6_results/person4_large"
EXPECTED_RAW_SHA256 = "4bfd4a3e0b976cbac34ba9d84b3f8f50d1d3a86542761dc072f7ee65ea1f24a9"
CASES = [(i, s) for i in ("BD1", "BD2") for s in ("zero", "one", "few", "many")]
# E/T/P/C/F: extraction /3, task types /2, priorities /2, clarity /2,
# usable shared-contract format /1 (the shared parser accepts JSON fences).
REVIEWS = {
    "tiiuae/Falcon3-7B-Instruct": [
        ((3,2,0,2,1), "Three distinct concerns with correct types. Kitchen MEDIUM understates tomorrow's preparation and tap URGENT assumes an immediate safety risk; grocery urgency may reflect the next-day deadline. Fenced JSON passes the shared contract."),
        ((3,2,0,2,1), "Three clear, correctly typed tasks. Kitchen urgency can reflect tomorrow's visit, but groceries MEDIUM are understated and tap URGENT lacks stated immediate safety evidence."),
        ((3,2,1,2,1), "All three concerns are clear and correctly typed; preparation HIGH is useful. Tap URGENT still assumes an immediate safety risk not explicitly stated."),
        ((3,2,1,2,1), "All three concerns are preserved with appropriate types and HIGH preparation priorities; tap URGENT needs human calibration to the actual leak severity."),
        ((3,2,1,1,0), "All four actions and correct types are visible, but the 220-token response ends at the sheets description and is unusable JSON. Batteries LOW under-ranks safety maintenance; Friday URGENT assumes Friday is within 24 hours."),
        ((3,2,1,2,1), "Four clear, correctly typed actions and the Friday deadline are preserved. Batteries LOW and Friday URGENT need review; the input does not establish an immediate safety failure or current weekday."),
        ((3,2,1,2,1), "Four distinct tasks and appropriate types; Friday is preserved. Batteries LOW under-ranks safety maintenance and URGENT assumes an unknown current weekday; routine dentist LOW is plausible."),
        ((3,2,1,2,1), "Four clear actions, appropriate types and explicit Friday deadline. Battery replacement LOW and library URGENT need calibration to actual safety status and time remaining."),
    ],
    "Qwen/Qwen2.5-14B-Instruct": [
        ((3,2,1,2,1), "Three concise, correctly typed concerns with no unsupported immediate urgency. Both preparation tasks MEDIUM understate the next-day visit; leak HIGH is reasonable."),
        ((3,2,1,2,1), "Three clear, correctly typed actions. Kitchen and tap HIGH are reasonable; groceries MEDIUM understate the same upcoming guest preparation."),
        ((3,2,1,2,1), "All three concerns are preserved with correct types. Both preparation tasks MEDIUM need review for tomorrow's visit; tap HIGH avoids assuming an immediate safety emergency."),
        ((3,2,1,2,1), "Three clear, correctly typed tasks. Preparation MEDIUM remains weak for tomorrow; the model does not invent urgent safety evidence for the tap."),
        ((3,2,2,2,1), "All four actions and Friday deadline preserved. APPOINTMENT/MAINTENANCE/ERRAND/CHORE are appropriate; safety maintenance and book HIGH, dentist MEDIUM and sheets LOW are reasonable."),
        ((3,2,2,2,1), "Four distinct, correctly typed actions with Friday retained. Preventive batteries MEDIUM is plausible without a stated detector failure; no unjustified URGENT or invented due date."),
        ((3,2,2,2,1), "Four clear actions, correct types, preserved Friday deadline and reasonable relative priorities. Washing/drying sheets is a harmless elaboration of the requested chore."),
        ((3,2,2,2,1), "Four clear, correctly typed actions and the Friday deadline. Priorities are reasonable without assuming the current weekday or an immediate detector failure."),
    ],
    "microsoft/Phi-3-medium-4k-instruct": [
        ((3,0,0,2,0), "Recognizes all three concerns clearly, but uses urgent_tasks/task/notes, omits task_type, and emits lowercase high rather than valid priority values. It does not meet the required schema."),
        ((3,2,1,2,1), "Three clear, correctly typed tasks. Groceries MEDIUM understate the upcoming visit; kitchen and tap HIGH are reasonable. Fenced JSON is accepted by the shared parser."),
        ((3,2,1,2,1), "All three concerns and correct types, with HIGH preparation priorities. Tap URGENT assumes an immediate safety risk not explicitly established; fenced JSON passes."),
        ((3,2,1,2,1), "Three clear, correctly typed tasks. Expanded cleaning details stay within the stated chore; tap URGENT still needs calibration to the actual leak risk."),
        ((3,0,0,1,0), "Four recognizable actions and Friday are present, but task/deadline/deperadline replace required title/type/priority/description fields. No task types or priorities are supplied."),
        ((3,1,1,1,0), "All four actions are visible but the response reaches 220 tokens without closing JSON. Library SHOPPING is incorrect; overdue is invented and contradicts before the due date. Dentist HIGH is unsupported and library MEDIUM is weak."),
        ((3,1,1,1,0), "All four actions are visible but closing JSON is truncated at 220 tokens. Library SHOPPING is incorrect and overdue is invented; the Friday deadline remains, though MEDIUM under-ranks it."),
        ((3,1,2,1,0), "Four concerns and Friday are present with reasonable relative priorities, but library APPOINTMENT is incorrect and overdue is unsupported. The response reaches 220 tokens without closing the JSON envelope."),
    ],
    "Qwen/Qwen3-14B": [
        ((3,2,1,2,1), "Three clear tasks with correct types and explicit tomorrow preparation. Tap URGENT assumes an immediate safety risk; HIGH preparation priorities are reasonable."),
        ((3,2,1,2,1), "Three clear, correctly typed concerns and HIGH preparation priorities. Tap URGENT needs human risk calibration; guest comfort does not itself establish immediate safety urgency."),
        ((3,2,1,2,1), "Three concise, correctly typed actions. Kitchen/tap HIGH are reasonable, while groceries MEDIUM understate the upcoming guest preparation."),
        ((3,2,1,2,1), "Three clear actions with correct types and no unsupported URGENT. Groceries MEDIUM still understate the same next-day preparation."),
        ((3,2,2,2,1), "All four concerns, appropriate types and explicit Friday deadline. Relative priorities are reasonable: safety maintenance/book HIGH and routine dentist/sheets MEDIUM."),
        ((3,2,2,2,1), "Four clear actions with correct types, the Friday deadline and sensible relative priorities. Batteries MEDIUM is plausible for preventive maintenance without a stated immediate failure."),
        ((3,2,1,2,1), "Four clear tasks, correct types and Friday deadline preserved. Battery replacement LOW under-ranks safety maintenance; remaining priorities are reasonable."),
        ((3,2,1,2,1), "Four clear, correctly typed actions and Friday deadline. Battery replacement LOW needs review; dentist MEDIUM, library HIGH and sheets LOW are reasonable."),
    ],
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def apply_reviews():
    path = FOLDER / "person4_large_results.csv"
    raw = FOLDER / "person4_large_raw_results.csv"
    if not raw.exists():
        raw.write_bytes(path.read_bytes())
    assert digest(raw.read_bytes()) == EXPECTED_RAW_SHA256, 'Raw outputs changed; inspect them and write new reviews instead of reusing these scores'
    with raw.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    expected = {(m, i, s): review for m, reviews in REVIEWS.items()
                for (i, s), review in zip(CASES, reviews)}
    assert len(rows) == len(expected) == 32
    assert {(r['model_id'],r['input_id'],r['shot_mode']) for r in rows} == set(expected)
    entries = []
    for row in rows:
        points, note = expected[row['model_id'],row['input_id'],row['shot_mode']]
        assert len(points) == 5 and all(0 <= p <= limit for p, limit in zip(points,(3,2,2,2,1)))
        row['quality_score_0_to_10'] = sum(points)
        row['review_notes'] = 'Assistant-assisted review; E/T/P/C/F=' + '/'.join(map(str,points)) + '. ' + note
        entries.append({"model_id":row['model_id'],"input_id":row['input_id'],"shot_mode":row['shot_mode'],
                        "points_E_T_P_C_F":points,"quality_score_0_to_10":sum(points),"note":note,
                        "raw_output_sha256":digest(row['raw_output'].encode('utf-8'))})
    with path.open('w',encoding='utf-8',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=fields,lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    # Preserve generation-time metadata verbatim alongside the later review record.
    metadata_path = FOLDER / 'person4_large_metadata.json'
    generation_metadata = FOLDER / 'person4_large_run_metadata.json'
    if not generation_metadata.exists():
        generation_metadata.write_bytes(metadata_path.read_bytes())
    metadata = json.loads(generation_metadata.read_text(encoding='utf-8'))
    metadata['review_attribution'] = 'Assistant-assisted explicit content review of all 32 responses; independent human approval not asserted. See person4_large_review_audit.json.'
    metadata_path.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    archive = ROOT / '.local-backups/p4-large-colab-export.zip'
    audit = {"reviewed_at_utc":datetime.now(timezone.utc).isoformat(),"reviewed_responses":32,
             "reviewer":"Codex assistant-assisted content review","independent_human_approval":False,
             "rubric":{"extraction":3,"task_types":2,"priorities":2,"clarity":2,"shared_contract_format":1},
             "calibration":"ERRAND or DEADLINE is acceptable for a library return when Friday is preserved. MEDIUM/HIGH can both be reasonable for preventive battery replacement without a stated failure; LOW merits review. URGENT requires explicit immediate safety evidence or a known deadline within 24 hours. Partial/truncated text can receive semantic credit, but format credit requires the shared schema. Fenced JSON is accepted by that parser.",
             "archive_sha256":digest(archive.read_bytes()) if archive.exists() else None,
             "raw_csv_sha256":digest(raw.read_bytes()),"reviewed_csv_sha256":digest(path.read_bytes()),
             "generation_metadata_sha256":digest(generation_metadata.read_bytes()),"reviews":entries}
    (FOLDER/'person4_large_review_audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    print('Applied 32 explicit reviews. Original generation CSV and metadata preserved.')


if __name__ == '__main__':
    apply_reviews()
