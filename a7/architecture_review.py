"""Apply response-inspected rubric corrections without changing raw generation evidence."""
import csv
import hashlib
import json
from pathlib import Path

from a7.review_results import review_csv

ROOT = Path(__file__).resolve().parents[1]
SMOL = 'HuggingFaceTB/SmolLM-360M-Instruct'
# Accuracy / adherence / completeness / clarity / supported, using the shared rubric.
# These corrections are assistant-inspected self-evaluations, pending student signoff.
SMOL_REVIEW = {
    'extraction-01': ([2,0,2,1,0], 'Mentions all three concerns but invents specific snack purchases, changes bathroom tap to bathtub, duplicates the repair and fails JSON-only format.'),
    'extraction-02': ([1,0,1,0,0], 'Conflates dentist/library/smoke-detector tasks, spreads Friday to unrelated tasks, invents cleaning chores and repeats them; no required JSON.'),
    'extraction-03': ([2,0,2,0,0], 'Mentions all concerns but repeats dialogue, makes unrequested action promises and supplies no structured task records.'),
    'extraction-04': ([1,0,1,0,0], 'Preserves only the electricity bill; omits vet and detergent, repeatedly assigns low priority without justification, and fails JSON format.'),
    'extraction-05': ([1,0,1,1,0], 'Falsely implies organizing the closet and mailing documents address refrigerator noise; invents specific tax-document contents and misses a usable refrigerator task.'),
    'summary-01': ([2,0,2,1,1], 'Includes removal, cleaning and grouping, but expands into unnecessary information requests rather than a concise one-sentence summary and is not JSON.'),
    'summary-02': ([1,0,2,0,0], 'Repeats the requested details but introduces calling at 3 PM instead of only an appointment after 3 PM; repetitive, non-JSON and not a concise summary.'),
    'summary-03': ([1,0,2,1,0], 'Restates the original concern but fabricates 10 and 20 percent consumption increases; repetitive provider dialogue and no JSON.'),
    'summary-04': ([3,0,2,0,1], 'Accurately restates books, due dates and weekend return, but repeats the same paragraph to the token limit; neither concise nor JSON.'),
    'summary-05': ([1,0,1,1,0], 'Mentions the source details but turns lamp checking into transporting the lamp, omits a useful towel step and repeats a truncated task list instead of concise JSON.'),
    'planning-01': ([2,0,1,1,1], 'Offers cleaning and bedding suggestions, but spends too much space on room/furniture setup, omits guest essentials and truncates; no JSON steps.'),
    'planning-02': ([1,0,1,1,1], 'Suggests a grocery list and repeats the budget but lacks price checking/running-total controls and is truncated after only two steps; no JSON.'),
    'planning-03': ([0,0,0,0,0], 'Produces Python code that sorts arbitrary steps, not a practical safe kitchen-cleaning plan or the required JSON.'),
    'planning-04': ([1,0,1,0,1], 'Includes packing but repeats the same step, lacks timing/transport/labeling and truncates; no JSON plan.'),
    'planning-05': ([0,0,0,0,0], 'Literal step 1/2/3 placeholders provide no energy-saving actions. Extra prose makes the response invalid JSON-only output.'),
}
for family in ('classification', 'priority'):
    for i in range(1, 6):
        SMOL_REVIEW[f'{family}-{i:02}'] = ([0,0,0,0,0],
            'Inspected response does not give the required correct single label; instead it generates role-play, repetition or unrequested narrative. Shared label-task scoring gives a minimum score of 1.')


def main():
    path = ROOT/'a7/results/architecture_benchmark.csv'
    references = json.loads((ROOT/'a7/architecture/response_review_reference.json').read_text(encoding='utf-8'))
    tiny_notes_path = ROOT/'a7/architecture/tinyllama_review_notes.json'
    tiny_refs_path = ROOT/'a7/architecture/tinyllama_review_reference.json'
    tiny_notes = json.loads(tiny_notes_path.read_text(encoding='utf-8')) if tiny_notes_path.exists() else {}
    tiny_refs = json.loads(tiny_refs_path.read_text(encoding='utf-8')) if tiny_refs_path.exists() else {}
    for family in ('classification', 'priority'):
        for i in range(1,6):
            tiny_notes[f'{family}-{i:02}'] = ([0,0,0,0,0],
                'Inspected response fails the shared single-label task rule: wrong label, all candidate labels, no selection, or a buried label in unrequested narrative. Minimum shared label-task score is 1.')
    review_csv(path)
    with path.open(encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames, list(reader)
    criterion_fields = ['task_accuracy_0_to_3', 'instruction_adherence_0_to_2',
                        'completeness_0_to_2', 'clarity_0_to_2', 'no_unsupported_details_0_to_1']
    audit = []
    for row in rows:
        if row['model_id'] in (SMOL, 'TinyLlama/TinyLlama-1.1B-Chat-v1.0') and row['status'] == 'ok':
            digest = hashlib.sha256(row['generated_output'].encode()).hexdigest()
            refs = references if row['model_id'] == SMOL else tiny_refs
            if digest != refs.get(row['prompt_id']):
                raise ValueError('Output changed since inspection; review new evidence before reapplying scores')
            reviews = SMOL_REVIEW if row['model_id'] == SMOL else tiny_notes
            points, notes = reviews[row['prompt_id']]
            row.update(dict(zip(criterion_fields, points)))
            row['self_evaluation_score_1_to_10'] = max(1, sum(points))
            row['review_notes'] = 'Assistant response-level review; student signoff pending. ' + notes
            audit.append(dict(model_id=row['model_id'], prompt_id=row['prompt_id'],
                              output_sha256=hashlib.sha256(row['generated_output'].encode()).hexdigest(),
                              criterion_points=points, notes=notes,
                              review_stage='assistant inspected; student signoff pending'))
    # Preserve the approved-account Llama assessments on future rebuilds instead
    # of replacing their response-level judgments with the automated first pass.
    llama_path = ROOT/'a7/architecture/llama_review_audit.json'
    if llama_path.exists():
        llama = json.loads(llama_path.read_text(encoding='utf-8'))
        entries = {entry['prompt_id']: entry for entry in llama['entries']}
        for row in rows:
            if row['model_id'] == llama['model_id'] and row['status'] == 'ok':
                entry = entries[row['prompt_id']]
                digest = hashlib.sha256(row['generated_output'].encode()).hexdigest()
                if digest != entry['response_sha256']:
                    raise ValueError('Llama output changed; inspect before reusing its scores')
                row.update(dict(zip(criterion_fields, entry['components'])))
                row['self_evaluation_score_1_to_10'] = max(1, sum(entry['components']))
                row['review_notes'] = 'Assistant response-level review; student signoff pending. ' + entry['notes']
                audit.append(dict(model_id=row['model_id'], prompt_id=row['prompt_id'],
                    output_sha256=digest, criterion_points=entry['components'], notes=entry['notes'],
                    review_stage='assistant inspected; student signoff pending'))
    temporary = path.with_suffix('.csv.tmp')
    with temporary.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    temporary.replace(path)
    (path.parent/'architecture_review_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(f'Scored {len(rows)} attempts; {len(audit)} response-inspected rubric reviews.')


if __name__ == '__main__':
    main()
