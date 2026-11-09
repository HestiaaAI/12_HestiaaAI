# Assignment 8 — Person 2

**Completed:** shared embeddings/retrieval, 15 assessed small-model RAG rows and
10 assessed small/full scaling rows. The returned Colab notebook ran without
saved errors. Scores and relevance labels are AI-assisted; student signoff is not
recorded. See [FINDINGS.md](FINDINGS.md) for measured conclusions and limitations.

## View and reproduce the analysis

Open [person2_retrieval_scaling.ipynb](../person2_retrieval_scaling.ipynb) for the
executed analysis: all 15 evaluation rows, all 25 actual answers and complete
retrieved passages, scaling tables and findings. It uses saved evidence by default,
with no network requests, model downloads or inference.

From the repository or extracted handoff root:

```sh
python -m pip install -r a8/person2/requirements.txt
python -m a8.person2_analysis
python -m unittest discover -s a8/tests -v
```

Requirements describe the tested local analysis environment. Actual hosted inference
versions are preserved in both run manifests: Python 3.13.18, torch 2.14.1+cpu,
NumPy 2.4.6, sentence-transformers 5.1.2, transformers 4.57.6, four PyTorch threads.
Do not pool these Colab timings with the earlier Mac measurements or Person 3's
separate matched cross-encoder run.

## Completed evidence

`a8/results/person2/completed-2026-11-09/` contains:

- `matrix/rows.jsonl`, `scaling/rows.jsonl`: unchanged raw prompts, full chunks,
  scores, answers, token counts and real end-to-end timings; 15 and 10 requests.
- Each experiment's `manifest.json`: frozen models/revisions/settings and runtime.
- `reviews.csv`: required-fact indices, unsupported-instruction deductions,
  relevant-hit ranks and rationale, bound to each entire raw row by SHA-256.
- `matrix_evaluation.csv`, `scaling_evaluation.csv`: complete assessed tables.
- `scaling_summary.csv`, `scaling_pairs.csv`: aggregate and per-query comparisons.
- `validation.json`: original download hashes, snapshot consistency and notebook checks.
- `input_bundle.zip`, `input_bundle_manifest.json`: exact code/data supplied to Colab.
- Original `reviews_template.csv` and `unreviewed_answers.csv`: retained as returned;
  the completed assessment is `reviews.csv`, not the unreviewed template.

[person2_colab_executed.ipynb](../person2_colab_executed.ipynb) is the unchanged
returned inference notebook. [person2_colab.ipynb](../person2_colab.ipynb) is its
repeat-run setup. See [COLAB.md](COLAB.md) for instructions. Fresh outputs require
new reviews and hashes; changed answers must not inherit old quality scores.

The original November 8 retrieval-only artifacts and indexes remain unchanged
under `results/person2/small-cpu-2026-11-08/`. Their historical findings are in
[RETRIEVAL_FINDINGS_2026-11-08.md](RETRIEVAL_FINDINGS_2026-11-08.md).

## Frozen generation and evaluation

The shared A6/A7-evaluated generator is `Qwen/Qwen2-0.5B-Instruct`, revision
`c540970f9e29518b1d8f06ab8b24cba66ad77b6d`. Person 3's unchanged generator/runner
uses CPU float32, greedy decoding, 128 new tokens, the same system/context prompt,
k=3 and four PyTorch threads. Both scaling datasets retain all five answer keys.
Expected answers, required facts and evidence quotes never enter model inputs.

Context/answer quality follow [the shared rubric](../person3/RUBRIC.md). Context
quality is exact supporting-quote coverage, not overall passage precision. Compound
facts must be fully conveyed. Unsupported material instructions incur deductions.
Student review may revise assisted judgments; the out-of-stock wording sensitivity
is explicitly analyzed in FINDINGS.md.

Noise is separately assessed: a relevant hit answers a requested part or provides
directly applicable conditions, handoff or approval context. Broad household-topic
similarity alone is insufficient. Noise = `(3 - relevant_hits) / 3`. Different
paragraph IDs are not automatically irrelevant, and redundant relevant text is not
automatically noise. Review reasons and relevant ranks are saved per request.

The validator rejects missing/duplicate rows or reviews, changed raw evidence,
incorrect prompts, stale corpus/query identities, wrong models and mismatched
matrix/scaling settings. End-to-end latency is measured jointly from query encoding
through decoded output; downloads, builds, warm-up and grading are excluded.

## Shared embedding/retrieval API

| Size | Hugging Face model | Dimensions | License | Token limit used |
|---|---|---:|---|---:|
| Small | sentence-transformers/all-MiniLM-L6-v2 | 384 | Apache 2.0 | 256 |
| Medium | sentence-transformers/all-mpnet-base-v2 | 768 | Apache 2.0 | 384 |
| Large | BAAI/bge-large-en-v1.5 | 1024 | MIT | 512 |

Sources: [MiniLM](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2),
[MPNet](https://huggingface.co/sentence-transformers/all-mpnet-base-v2),
[BGE](https://huggingface.co/BAAI/bge-large-en-v1.5). Actual compatibility tests and
immutable revisions are in `results/person2/model_smoke_tests.json`. BGE applies
its documented query instruction only to query text. The small-model maximum chunk
length is 233 tokens; no silent truncation occurs. Model families differ in training
and architecture, so dimension alone cannot explain quality differences.

```python
from pathlib import Path
from a8.corpus import load_chunks
from a8.retrieval import load_encoder, build_index, search, save_index, load_index

encoder = load_encoder('small')  # accepts medium and large as well
index = build_index(load_chunks('hybrid', 'full'), encoder, encoder.a8_metadata)
hits = search(index, 'Where is the cordless drill?', encoder, top_k=3)
save_index(index, Path('a8/results/my-index'))
index = load_index(Path('a8/results/my-index'), index.manifest)
```

The index uses normalized float32 NumPy vectors and stable exact cosine ranking,
sufficient for 10–30 chunks. Hits retain full text, source IDs, rank and score.
Persisted checksums protect vector/metadata alignment. Supply the expected corpus
and model manifest when loading a saved index. Similarities are not confidence
probabilities and are not calibrated across encoders.

Person 3 owns the matched cross-encoder comparison; Person 4 owns the combined
failure/improvement/design analysis and final team submission ZIP. This is the
completed Person 2 contribution, not a claim that every team section was rerun here.
