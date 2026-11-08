# Assignment 8 — Person 2

Implemented: shared sentence-transformer indexing, exact cosine top-k retrieval,
portable saved indexes, 15 small-model retrieval rows and 10 controlled scaling
retrieval rows. Generation and subjective quality assessment are **pending**
Person 3's shared generator/prompt/rubric. These are not 15 completed RAG evaluations.

## Setup and run

From the repository or extracted submission root, with `a8/` available:

```sh
python -m venv .venv
# Activate the environment using your operating system's normal command.
python -m pip install -r a8/person2/requirements.txt
python -m unittest discover -s a8/tests -v
python -m a8.person2_experiments --output-dir a8/results/person2/my-new-run --device cpu
```

Initial execution downloads the free embedding weights from Hugging Face; weights
stay in the normal external Hugging Face cache. No paid inference service or API
key is required. Requirements record the tested Python 3.13 environment; other
platforms may need compatible PyTorch packages and must record a separate run.

Open `a8/person2_retrieval_scaling.ipynb` for analysis of saved measurements. Its
default mode performs no inference or network requests. Set `RUN_RETRIEVAL=True`
with a fresh relative output directory to run the small-model retrieval experiments.
Run the notebook from the repo root or `a8/`. The handoff notebook is integrated
into the final `rag_system.ipynb` by Person 4, not a replacement for the full team submission.

## Three selected embedding models

| Size | Hugging Face model | Dimensions | License | Context limit used |
|---|---|---:|---|---:|
| Small | sentence-transformers/all-MiniLM-L6-v2 | 384 | Apache 2.0 | 256 |
| Medium | sentence-transformers/all-mpnet-base-v2 | 768 | Apache 2.0 | 384 |
| Large | BAAI/bge-large-en-v1.5 | 1024 | MIT | 512 |

Model cards: [MiniLM](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2),
[MPNet](https://huggingface.co/sentence-transformers/all-mpnet-base-v2),
[BGE](https://huggingface.co/BAAI/bge-large-en-v1.5). Different training/architectures
also change across these choices; dimensions alone cannot explain any difference.

Use `load_encoder(size, device='cpu', revision=None)` to resolve and record an
immutable revision. BGE's documented retrieval instruction is applied to queries
only; stored passages use their original text. Every encoding checks token length
before inference and rejects overflow rather than silently truncating. The actual
small-model corpus maximum is 233 tokens, below its standard 256-token limit.

## Shared retrieval API

```python
from a8.corpus import load_chunks
from a8.retrieval import load_encoder, build_index, search, save_index, load_index
from pathlib import Path

encoder = load_encoder('small')  # medium/large work through the same interface
index = build_index(load_chunks('hybrid', 'full'), encoder, encoder.a8_metadata)
hits = search(index, 'Where is the cordless drill?', encoder, top_k=3)
save_index(index, Path('a8/results/my-index'))
index = load_index(Path('a8/results/my-index'), index.manifest)
```

Hits include rank, chunk ID, full text, document, section, paragraph IDs and cosine
score. Scores are similarities, not confidence probabilities, and are not calibrated
across models. Indexes use normalized float32 vectors and stable descending ranking;
NumPy exact search is sufficient for this 10–30-chunk corpus. Checksums detect stale
metadata and vector artifacts. For reuse, supply the expected corpus/model manifest.

## Generation handoff to Person 3

`attach_generation(output_dir, generate_answer, generator_manifest)` consumes saved
contexts and calls `generate_answer(query, retrieved_chunks)`; neither expected
answers nor supporting quotes are passed to this callable. Return a dictionary:

```python
{
    'answer': actual_generated_answer,
    'prompt': exact_rendered_prompt,
    'generation_ms': measured_generation_ms,
    'context_truncated': False,
}
```

Freeze the generator ID/revision, precision, prompt template/version, decoding,
output cap, hardware and rubric in `generator_manifest` before collecting final
answers. Use an A6/A7-evaluated generator consistently across all nine team
configurations. Do not substitute a new model to improve only one person's rows.
The adapter saves actual errors, resumes existing row IDs without rerunning them,
and refuses different generator settings in the same directory. Failed generations
remain recorded; retry with a separate output copy/run and retain original evidence.

The adapter can run generation after retrieval; therefore it reports a **sum of
stage latencies**, not observed end-to-end latency. `end_to_end_ms` remains empty.
Person 3's final joint runner must measure end-to-end requests and apply the shared
rubric. Context/answer quality columns intentionally remain empty until reviewed.

## Evidence and timing

`a8/results/person2/small-cpu-2026-11-08/` contains the measured run:

- `run_manifest.json`: resolved revision, source/data hashes, settings and environment.
- `retrieval.jsonl`: 15 matrix + 10 scaling rows with complete retrieved contexts.
- `retrieval_matrix.csv`, `retrieval_scaling.csv`: flat tables with pending fields empty.
- `indexes/`: aligned compressed vectors, chunk metadata and manifests.
- `index_stats.json`: separate build time, corpus/chunk counts and raw vector memory.
- `scaling_latency_samples.json`: 10 interleaved warmed repetitions per query/dataset.

All request timings exclude download/model load and index construction. Timing
separates query encoding and similarity/ranking; the outer retrieval timing also
includes validation and hit assembly. CPU is the measured device. Builds are cold
relative to each chunk set, with fixed strategy built first, so first-build overhead
is not evidence that fixed chunking inherently encodes more slowly.

Source recall and reciprocal rank use paragraph IDs and can overestimate evidence
when a paragraph is split. Exact evidence quote coverage inspects actual chunk text
with case/whitespace normalization. It is a diagnostic, not a human relevance or
answer-quality score. See `FINDINGS.md` for measured scaling observations.
