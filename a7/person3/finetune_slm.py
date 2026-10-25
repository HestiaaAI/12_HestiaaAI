"""Fine-tune a fresh copy of Person 1's original SLM on Person 2's facts.

The five questions and documents are read from a7/slm/knowledge_base.
Baseline prompts are question plus a newline, matching pack_prompt with no
retrieved documents. Generation stays on CPU with seed 42, temperature 0.7,
and 100 new characters. The original checkpoint file is not overwritten.
"""
from __future__ import annotations

import copy
import csv
import json
import time
from pathlib import Path

import torch
import torch.nn.functional as F

from a7.slm.handoff import DEFAULT_CHECKPOINT, generate, load_selected, state_hash

ROOT = Path(__file__).resolve().parents[2]
SLM = ROOT / "a7" / "slm"
OUT_DIR = Path(__file__).resolve().parent / "results"
FINETUNED = SLM / "checkpoints" / "finetuned_person3.pt"
BASELINE_CSV = SLM / "results" / "person2_rag_colab" / "person2_baseline.csv"

GENERATION = {"seed": 42, "temperature": 0.7, "max_new_tokens": 100}
FINE_TUNE = {
    "steps": 300,
    "batch_size": 16,
    "learning_rate": 0.001,
    "weight_decay": 0.01,
    "seed": 42,
    "device": "cpu",
    "threads": 2,
}


def calculate_loss(logits, targets):
    batch, length, vocab = logits.shape
    return F.cross_entropy(logits.reshape(batch * length, vocab), targets.reshape(batch * length))


def get_batch(source, context_length, batch_size, device):
    starts = torch.randint(0, len(source) - context_length, (batch_size,))
    x = torch.stack([source[i : i + context_length] for i in starts])
    y = torch.stack([source[i + 1 : i + context_length + 1] for i in starts])
    return x.to(device), y.to(device)


def encode(text, vocab):
    stoi = {ch: i for i, ch in enumerate(vocab)}
    unknown = sorted(set(text) - set(stoi))
    if unknown:
        raise ValueError(f"Fine-tune text uses characters outside the SLM vocabulary: {unknown!r}")
    return torch.tensor([stoi[ch] for ch in text], dtype=torch.long)


def continuation(full_text, prompt):
    if not full_text.startswith(prompt):
        raise ValueError("Generated text did not start with the prompt.")
    return full_text[len(prompt) :]


def baseline_prompt(question: str) -> str:
    """Same string Person 2 passed to generate when no document was retrieved."""
    return question + "\n"


def training_examples(documents, questions):
    by_id = {doc["id"]: doc["text"] for doc in documents}
    examples = [doc["text"] for doc in documents]
    for item in questions:
        fact = by_id[item["source_document_ids"][0]]
        examples.append(baseline_prompt(item["question"]) + fact)
    if len(examples) < 10:
        raise ValueError("Need at least 10 fine-tuning examples.")
    return examples


def score_response(response, facts):
    lowered = response.lower()
    hits = [fact for fact in facts if fact in lowered]
    accuracy = round(10 * len(hits) / len(facts)) if facts else 0
    relevance = min(10, 4 + 3 * len(hits)) if hits else (2 if response.strip() else 1)
    notes = (
        f"Fact-phrase check found {len(hits)}/{len(facts)} expected facts "
        f"({', '.join(hits) if hits else 'none'}). "
        "A hit only means the phrase occurs in the continuation."
    )
    return accuracy, relevance, len(hits) == 0, notes


def load_person2_baselines():
    with BASELINE_CSV.open(newline="", encoding="utf-8") as handle:
        return {row["question_id"]: row for row in csv.DictReader(handle)}


def run():
    torch.set_num_threads(FINE_TUNE["threads"])
    documents = json.loads((SLM / "knowledge_base" / "documents.json").read_text())
    questions = json.loads((SLM / "knowledge_base" / "questions.json").read_text())
    person2 = load_person2_baselines()
    model, vocab = load_selected()
    original_hash = state_hash(model)
    before_state = copy.deepcopy(model.state_dict())
    examples = training_examples(documents, questions)
    for text in examples:
        encode(text, vocab)

    before = []
    for item in questions:
        prompt = baseline_prompt(item["question"])
        full = generate(model, vocab, prompt, **GENERATION)
        text = continuation(full, prompt)
        accuracy, relevance, unsupported, notes = score_response(text, item["expected_facts"])
        reference = person2[item["question_id"]]
        before.append({
            "question_id": item["question_id"],
            "prompt": prompt,
            "response": text,
            "person2_baseline_response": reference["response"],
            "matches_person2_baseline": text == reference["response"],
            "state_sha256": original_hash,
            "factual_accuracy": accuracy,
            "relevance": relevance,
            "unsupported_information": unsupported,
            "review_notes": notes,
        })

    corpus = ("\n".join(examples) + "\n") * 40
    train_data = encode(corpus, vocab)
    context = model.context_length
    if len(train_data) <= context:
        raise ValueError("Fine-tune corpus is shorter than the context window.")

    torch.manual_seed(FINE_TUNE["seed"])
    device = torch.device(FINE_TUNE["device"])
    model.to(device)
    model.train()
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=FINE_TUNE["learning_rate"], weight_decay=FINE_TUNE["weight_decay"]
    )
    losses = []
    started = time.perf_counter()
    for _step in range(FINE_TUNE["steps"]):
        xb, yb = get_batch(train_data, context, FINE_TUNE["batch_size"], device)
        optimizer.zero_grad()
        loss = calculate_loss(model(xb), yb)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())
    elapsed = time.perf_counter() - started

    model.to("cpu")
    model.eval()
    tuned_hash = state_hash(model)
    changed = any(
        not torch.equal(before_state[name].cpu(), tensor.cpu())
        for name, tensor in model.state_dict().items()
    )
    after = []
    for item in questions:
        prompt = baseline_prompt(item["question"])
        full = generate(model, vocab, prompt, **GENERATION)
        text = continuation(full, prompt)
        accuracy, relevance, unsupported, notes = score_response(text, item["expected_facts"])
        after.append({
            "question_id": item["question_id"],
            "prompt": prompt,
            "response": text,
            "state_sha256": tuned_hash,
            "factual_accuracy": accuracy,
            "relevance": relevance,
            "unsupported_information": unsupported,
            "review_notes": notes,
        })

    FINETUNED.parent.mkdir(parents=True, exist_ok=True)
    saved = torch.load(DEFAULT_CHECKPOINT, map_location="cpu", weights_only=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "config": saved["config"],
            "vocab": vocab,
            "source_checkpoint": str(DEFAULT_CHECKPOINT),
        },
        FINETUNED,
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_checkpoint": str(DEFAULT_CHECKPOINT),
        "original_state_sha256": original_hash,
        "finetuned_state_sha256": tuned_hash,
        "weights_updated": changed,
        "architecture": "TinyTransformerLM embedding 48, heads 2, layers 1, feedforward 192, context 32",
        "knowledge_base": "a7/slm/knowledge_base",
        "examples": examples,
        "example_count": len(examples),
        "documents": documents,
        "questions": questions,
        "prompt_rule": "question plus one newline, matching Person 2 baseline prompts",
        "generation": {**GENERATION, "device": "cpu", "threads": 2},
        "fine_tune": FINE_TUNE,
        "initial_loss": losses[0],
        "final_loss": losses[-1],
        "training_seconds": round(elapsed, 2),
        "loss_history_every_50": losses[::50] + [losses[-1]],
        "baseline_matches_person2": sum(item["matches_person2_baseline"] for item in before),
        "before": before,
        "after": after,
        "torch_version": torch.__version__,
    }
    (OUT_DIR / "finetune_results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({
        "weights_updated": changed,
        "baseline_matches_person2": payload["baseline_matches_person2"],
        "initial_loss": round(losses[0], 4),
        "final_loss": round(losses[-1], 4),
        "seconds": round(elapsed, 2),
        "after_accuracy": [item["factual_accuracy"] for item in after],
    }, indent=2))
    return payload


if __name__ == "__main__":
    run()
