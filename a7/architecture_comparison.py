"""Validate teammate evidence and build Assignment 2 Part 4 Markdown."""
import json
from pathlib import Path


def escape_cell(value):
    return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('\n', '<br>')


def comparison_markdown(path: Path, manifest_path: Path):
    if not path.exists():
        return ('## Part 4: comparison pending teammate evidence\n\n'
                'Person 2 must supply the five questions, baseline and all 20 RAG responses. '
                'Person 3 must supply the five fine-tuned responses and weight-change evidence. '
                'No accuracy winner can be reported yet.\n\n'
                '| Question | Baseline SLM | SLM + RAG | Fine-tuned SLM |\n'
                '|---|---|---|---|\n' +
                '\n'.join(f'| Q{i} — awaiting shared question | Pending | Pending | Pending |' for i in range(1, 6)))
    evidence = json.loads(path.read_text(encoding='utf-8'))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    original = manifest['state_sha256']
    if evidence['original_state_sha256'] != original:
        raise ValueError('Comparison must originate from the selected original checkpoint')
    if evidence['generation'] != {**manifest['generation'], 'device': 'cpu', 'threads': 2}:
        raise ValueError('Generation settings do not match the common comparison settings')
    questions = evidence['questions']
    if len(questions) != 5 or len({q['question_id'] for q in questions}) != 5:
        raise ValueError('Exactly five distinct shared questions required')
    means = {k: 0 for k in (1, 2, 3, 5)}
    for q in questions:
        if not q['question'] or not q['expected_facts'] or not q['source_document_ids']:
            raise ValueError('Each question needs expected facts and supporting document IDs')
        if sorted(r['top_k'] for r in q['rag']) != [1, 2, 3, 5]:
            raise ValueError('Each question requires exactly four Top-K results')
        for condition, row in [('baseline', q['baseline']), ('fine_tuned', q['fine_tuned'])] + [('rag', r) for r in q['rag']]:
            if not isinstance(row['response'], str) or not isinstance(row['prompt'], str):
                raise ValueError('Preserve actual prompt and continuation-only response strings')
            if not row['prompt'] or set(row['prompt']) - set(manifest['vocab']):
                raise ValueError('Prompt contains characters unsupported by the selected vocabulary')
            if condition != 'fine_tuned' and row['state_sha256'] != original:
                raise ValueError('Baseline and RAG must preserve original weights')
            if condition == 'fine_tuned' and row['state_sha256'] == original:
                raise ValueError('Fine-tuning evidence must demonstrate changed weights')
            for metric in ('factual_accuracy', 'relevance'):
                score = row[metric]
                if isinstance(score, bool) or not isinstance(score, (int, float)) or not 1 <= score <= 10:
                    raise ValueError(f'{metric} must be a human-reviewed 1–10 score')
            if not isinstance(row['unsupported_information'], bool) or not row['review_notes']:
                raise ValueError('Document unsupported information and human review notes')
            if condition == 'rag':
                if row['visible_context'] != row['prompt'][-manifest['config']['context_length']:]:
                    raise ValueError('RAG visible context must equal the actual last 32 characters')
                if len(row['retrieved_document_ids']) != row['top_k']:
                    raise ValueError('Retrieved document count must match Top-K')
                means[row['top_k']] += row['factual_accuracy']/5
    chosen = min(means, key=lambda k: (-means[k], k))
    table = ['## Part 4: baseline, RAG and fine-tuning', '',
             f'RAG Top-K = {chosen}, selected by highest mean factual accuracy with ties resolved by lower K. '
             'Selection uses these same five evaluation questions; this is descriptive, not held-out evaluation.', '',
             '| Question | Baseline SLM | SLM + RAG | Fine-tuned SLM |', '|---|---|---|---|']
    totals = {c: {'accuracy': 0, 'relevance': 0, 'unsupported': 0} for c in ('Baseline', 'RAG', 'Fine-tuned')}
    notes = []
    for q in questions:
        rag = next(r for r in q['rag'] if r['top_k'] == chosen)
        rows = [q['baseline'], rag, q['fine_tuned']]
        table.append('| ' + ' | '.join(escape_cell(v) for v in
                     [q['question_id'] + ': ' + q['question']] + [r['response'] for r in rows]) + ' |')
        for name, row in zip(totals, rows):
            totals[name]['accuracy'] += row['factual_accuracy']/5
            totals[name]['relevance'] += row['relevance']/5
            totals[name]['unsupported'] += int(row['unsupported_information'])
            notes.append(f"- {escape_cell(q['question_id'])}, {name}: {escape_cell(row['review_notes'])}")
    table += ['', '| Condition | Mean factual accuracy /10 | Mean relevance /10 | Responses with unsupported information /5 |', '|---|---|---|---|']
    table += [f"| {name} | {v['accuracy']:.2f} | {v['relevance']:.2f} | {v['unsupported']} |" for name, v in totals.items()]
    best = max(v['accuracy'] for v in totals.values())
    winners = ', '.join(n for n,v in totals.items() if abs(v['accuracy']-best) < 1e-9)
    table += ['', '### Quality and consistency evidence', '', *notes,
              '', 'Consistency here means the observed pattern across five questions. Single-seed runs do not measure stability across random seeds.',
              '', '### Step 4.2 final analysis', '',
              f'1. {winners} achieved the highest mean factual accuracy ({best:.2f}/10) on these five questions; this small set does not establish general performance.',
              '2. Fine-tuning updated weights; baseline and RAG retained the original selected checkpoint state.',
              '3. RAG is easier to maintain as facts change because knowledge documents can be updated without retraining model weights.',
              '4. For a startup with frequently changing policies, retrieval is the maintenance-oriented choice, provided the model can use the retrieved context. Interpret this classroom SLM’s actual quality scores in light of its 32-character window.',
              '5. RAG and fine-tuning can be combined: tune the model’s behavior and retrieve current facts at inference time. That combined condition was not tested here.']
    return '\n'.join(table)
