"""Adapt the supplied class TF-IDF RAG pipeline to the original character SLM.

Class source: class_rag_source.ipynb, cells 10/14/18/19. Retrieval arithmetic
is unchanged; min_score=0 includes zero-overlap documents for the required K=5.
Only generator wiring, vocabulary-compatible packing and evidence export change.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import time

import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from a7.slm.handoff import generate, load_selected, state_hash

ROOT = Path(__file__).resolve().parent
TOP_K_VALUES = (1, 2, 3, 5)
GENERATION = {'seed': 42, 'temperature': .7, 'max_new_tokens': 100, 'device': 'cpu', 'threads': 2}


def build_index(documents):
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
    document_matrix = vectorizer.fit_transform([d['title'] + ' ' + d['text'] for d in documents])
    return vectorizer, document_matrix


def retrieve(query, documents, vectorizer, document_matrix, top_k=2, min_score=0.0):
    """Return top matching document dictionaries with scores."""
    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(query_vector, document_matrix)[0]
    indices = scores.argsort()[::-1][:top_k]
    return [{**documents[i], "score": float(scores[i])} for i in indices if scores[i] >= min_score]


def validate_text(text, vocab):
    unknown = sorted(set(text) - set(vocab))
    if not text or unknown:
        raise ValueError(f'Prompt must be nonempty and use the class vocabulary; unsupported: {unknown!r}')


def pack_prompt(question, matches):
    # The class's labels/citations contain symbols absent from this vocabulary.
    # Keep ranked evidence and the question, using only supported separators.
    context = '\n'.join(d['text'] for d in matches)
    return (context + '\n' if context else '') + question + '\n'


def verify_checkpoint(path, manifest):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != manifest['checkpoint_sha256']:
        raise ValueError('Checkpoint file differs from the exact Person 1 handoff')


def _write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows({k: json.dumps(v) if isinstance(v, (list, dict)) else v
                          for k, v in row.items()} for row in rows)


def run_experiments(checkpoint=ROOT/'checkpoints/selected_baseline.pt', output_dir=ROOT/'results/person2_rag_colab'):
    output_dir = Path(output_dir)
    if any((output_dir/name).exists() for name in ['person2_baseline.csv', 'person2_rag.csv', 'person2_rag.json']):
        raise FileExistsError('Preserve previous results and choose a fresh output folder before rerunning')
    manifest = json.loads((ROOT/'results/selected_checkpoint.json').read_text())
    verify_checkpoint(checkpoint, manifest)
    torch.set_num_threads(2)
    model, vocab = load_selected(checkpoint)
    initial = state_hash(model)
    if initial != manifest['state_sha256']:
        raise ValueError('Loaded tensor state differs from the original selected checkpoint')
    documents = json.loads((ROOT/'knowledge_base/documents.json').read_text())
    questions = json.loads((ROOT/'knowledge_base/questions.json').read_text())
    if len(documents) < 5 or len({d['id'] for d in documents}) != len(documents):
        raise ValueError('At least five uniquely identified documents are required')
    if len(questions) != 5 or len({q['question_id'] for q in questions}) != 5:
        raise ValueError('Exactly five uniquely identified evaluation questions are required')
    for doc in documents:
        validate_text(doc['text'], vocab)
    for question in questions:
        validate_text(question['question'], vocab)
    vectorizer, matrix = build_index(documents)
    output_dir.mkdir(parents=True, exist_ok=True)
    baselines, rag_rows, results = [], [], []
    context_length = manifest['config']['context_length']
    for question in questions:
        q = {**question, 'rag': []}
        for k in (0, *TOP_K_VALUES):
            matches = retrieve(q['question'], documents, vectorizer, matrix, top_k=k) if k else []
            if len(matches) != k:
                raise ValueError('Top-K retrieval returned an unexpected number of documents')
            prompt = pack_prompt(q['question'], matches)
            validate_text(prompt, vocab)
            started = time.perf_counter()
            generated = generate(model, vocab, prompt, seed=42, temperature=.7, max_new_tokens=100)
            elapsed = time.perf_counter() - started
            if not generated.startswith(prompt):
                raise ValueError('Class generator did not return prompt plus continuation')
            visible = prompt[-context_length:]
            response = {
                'prompt': prompt, 'response': generated[len(prompt):], 'state_sha256': initial,
                'response_quality': None, 'factual_accuracy': None, 'relevance': None, 'unsupported_information': None,
                'review_notes': 'Pending response-level review; no quality score is invented.',
                'generation_seconds': elapsed, 'visible_context': visible,
                'prompt_characters': len(prompt), 'context_truncated': len(prompt) > context_length,
                'expected_facts_visible': {fact: fact in visible for fact in q['expected_facts']},
            }
            flat = {'question_id': q['question_id'], 'question': q['question'], **response}
            if k:
                response.update(top_k=k, retrieved_document_ids=[d['id'] for d in matches],
                                retrieval_scores=[d['score'] for d in matches])
                q['rag'].append(response)
                rag_rows.append({**flat, 'top_k': k, 'retrieved_document_ids': response['retrieved_document_ids'],
                                 'retrieval_scores': response['retrieval_scores']})
                _write_csv(output_dir/'person2_rag.csv', rag_rows)
            else:
                q['baseline'] = response
                baselines.append(flat)
                _write_csv(output_dir/'person2_baseline.csv', baselines)
            print(q['question_id'], 'baseline' if not k else f'top-{k}', f'{elapsed:.3f}s', flush=True)
        results.append(q)
    final = state_hash(model)
    if final != initial:
        raise ValueError('RAG weights changed; discard this run as an invalid no-training comparison')
    result = {
        'original_state_sha256': initial, 'final_state_sha256': final, 'weights_unchanged': True,
        'generation': GENERATION, 'retrieval': {'method': 'class TF-IDF + cosine similarity',
            'stop_words': 'english', 'ngram_range': [1, 2], 'min_score': 0.0, 'top_k': list(TOP_K_VALUES)},
        'checkpoint_config': manifest['config'], 'questions': results,
        'review_complete': False,
        'environment': {'python': platform.python_version(), 'platform': platform.platform(),
            'packages': {p: importlib.metadata.version(p) for p in ['torch','numpy','scikit-learn','pandas']}},
        'source_hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT/'class_rag_source.ipynb', ROOT/'class_model.py',
                      ROOT/'knowledge_base/documents.json', ROOT/'knowledge_base/questions.json']},
    }
    (output_dir/'person2_rag.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, default=ROOT/'checkpoints/selected_baseline.pt')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'results/person2_rag_colab')
    args = parser.parse_args()
    run_experiments(args.checkpoint, args.output_dir)
