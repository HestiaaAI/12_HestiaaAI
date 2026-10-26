"""Join original peer exports, retaining raw scores and explicit response reviews."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Continuation-level assessment against the same five household facts. A phrase
# occurrence is not a fully correct answer when the continuation contradicts it.
REVIEWS = {
    'Q1': (1, 2, 'Does not answer Monday; talks about the shed and invents soap under the hall.'),
    'Q2': (1, 2, 'Does not answer Friday; repeats laundry/Monday instead of answering trash day.'),
    'Q3': (4, 5, 'Includes the correct hall location but also explicitly places guest towels in the shed. Partial credit only; contradictory and repetitive.'),
    'Q4': (5, 5, 'Begins with the partial correct phrase spare in the shed, then invents soap under the shed and mixes unrelated facts. Partial credit, not a clean answer.'),
    'Q5': (1, 4, 'Recognizes dish soap but repeatedly gives the wrong location under the shed instead of under the sink.'),
}
REVIEW_RESPONSE_SHA256 = {
    'Q1': 'fd6644faa54643bce9f32b66af77417188d361e5a059ff5079260a029811bf53',
    'Q2': '15bc70cb554f3ea98117f871135edc2d0b3f5ba2e515e53cdfaf955ef1a41099',
    'Q3': '59c4e02a6842c414b85fe3b1262054b3835cf90f8bf575dd6a56ba2913e95a9e',
    'Q4': '9807f8921379b75ab40e9377cdea202b5cd7db9b6856832adbbdde6a97532139',
    'Q5': '2b9c5524c974b43f8ff48a4180ebec5541d08939a26a5b2f978178e6c8df41a2',
}


def integrate(root=ROOT):
    rag_path = root/'a7/slm/results/person2_rag_colab/person2_rag_reviewed.json'
    tuned_path = root/'a7/person3/results/finetune_results.json'
    rag = json.loads(rag_path.read_text(encoding='utf-8'))
    tuned = json.loads(tuned_path.read_text(encoding='utf-8'))
    if (rag['original_state_sha256'] != tuned['original_state_sha256']
            or rag['generation'] != tuned['generation']
            or not tuned['weights_updated']
            or tuned['finetuned_state_sha256'] == tuned['original_state_sha256']):
        raise ValueError('Peer checkpoint lineage, generation or changed-weight evidence mismatch')
    before = {r['question_id']: r for r in tuned['before']}
    after = {r['question_id']: r for r in tuned['after']}
    question_metadata = {q['question_id']: q for q in tuned['questions']}
    if set(before) != set(after) or set(after) != set(REVIEWS):
        raise ValueError('Expected exactly five fine-tuning questions')
    for question in rag['questions']:
        key = question['question_id']
        for field in ('question', 'expected_facts', 'source_document_ids'):
            if question[field] != question_metadata[key][field]:
                raise ValueError(f'{key}: shared question drift')
        for field in ('prompt', 'response', 'state_sha256'):
            if question['baseline'][field] != before[key][field]:
                raise ValueError(f'{key}: pre-training baseline mismatch')
        row = copy.deepcopy(after[key])
        if hashlib.sha256(row['response'].encode()).hexdigest() != REVIEW_RESPONSE_SHA256[key]:
            raise ValueError(f'{key}: changed response requires a fresh review')
        if row['state_sha256'] != tuned['finetuned_state_sha256']:
            raise ValueError(f'{key}: inconsistent fine-tuned hash')
        row['source_automatic_scores'] = {f: row[f] for f in
            ('factual_accuracy', 'relevance', 'unsupported_information', 'review_notes')}
        row['factual_accuracy'], row['relevance'], row['review_notes'] = REVIEWS[key]
        row['unsupported_information'] = True
        row['response_sha256'] = hashlib.sha256(row['response'].encode()).hexdigest()
        question['fine_tuned'] = row
    rag['integration'] = dict(
        source_files=[str(p.relative_to(root)).replace('\\', '/') for p in (rag_path, tuned_path)],
        canonical_lf_source_sha256={str(p.relative_to(root)).replace('\\', '/'):
            hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for p in (rag_path, tuned_path)},
        baseline_matches=5,
        scoring_method='Preserve Person 2 baseline/RAG 1–10 reviews. Review fine-tuned continuations on the same 1–10 scale: 1 no correct answer, partial credit for correct but incomplete/contradictory answers, 10 fully correct without contradiction. Source phrase-match scores (including zeros) retained separately; not averaged with reviewed scores.',
        limitations='Five questions are also present in fine-tuning examples; no held-out generalization claim. Single seed. Changed-state evidence is reported by Person 3; see independent reproduction report for local verification.',
        training={k: tuned[k] for k in ('example_count','initial_loss','final_loss','training_seconds',
            'fine_tune','torch_version','original_state_sha256','finetuned_state_sha256','weights_updated')})
    reproduction=root/'a7/results/architecture/finetune_reproduction_check.json'
    if reproduction.exists():
        rag['integration']['independent_reproduction']=json.loads(reproduction.read_text())
    out = root/'a7/architecture/inputs/slm_comparison.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rag, indent=2)+'\n', encoding='utf-8')
    return rag


if __name__ == '__main__':
    result=integrate()
    print('Integrated five matching baselines, 20 RAG and five reviewed fine-tuned continuations.')
