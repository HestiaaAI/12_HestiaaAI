# Person 2 — Colab handoff

Status: the user completed the Colab RAG run and exported its AI-assisted review. Raw CSV/JSON, reviewed JSON and validation record are preserved in `a7/slm/results/person2_rag_colab/`. All 25 responses failed to answer the household questions; see `a7/person2/review/RAG_ANALYSIS.md`. Local validation recomputed retrieval and compared all raw/reviewed outputs without rerunning model generation. The executed Colab notebook is saved at `a7/slm/person2_rag_colab.ipynb`; its 25 displayed responses, review entries and five analysis answers were checked against the exported evidence. It contains no saved error outputs. All 100 HF benchmark generations now succeeded on a Tesla T4 with NF4/FP32 compute. Raw results, environment metadata and verification are saved in `a7/results/person2_nf4_colab/`, and the executed benchmark notebook is saved at `a7/person2_benchmark_colab.ipynb`. All 100 benchmark responses have hash-bound AI-assisted assessments, saved in `a7/results/person2_benchmark.csv`. The 90-case local-cost table is calculated in `a7/results/local_costs.csv`. The executed `a7/person2_analysis.ipynb` provides the tables, figures, workload, formulas and limitations. Student signoff on the assisted assessments and agreement with Person 3 on the API comparison assumptions remain pending.

## Files and responsibilities

- `a7/person2_benchmark_colab.ipynb`: four assigned Hugging Face models × 25 shared prompts = 100 runs.
- `a7/slm/person2_rag_colab.ipynb`: original Person 1 SLM, five baseline responses and 20 RAG responses (K=1/2/3/5).
- `a7/slm/knowledge_base/`: five fictional documents, fixed questions, expected facts and source IDs. Share these with Persons 3 and 4 now; changing them later invalidates the shared comparison.
- `a7/slm/class_rag_source.ipynb`: supplied class notebook with outputs/interactive metadata cleared; cell source retained. `class_rag_provenance.json` records source hashes and compatibility changes.
- **Team integration remaining:** student inspection of assisted ratings, Person 3 agreement on token/cost boundaries, and Person 4 integration into the combined notebooks. Person 2 has supplied all 100 assessed benchmark rows and 90 local-cost scenarios. The Colab RAG experiment, review and five analysis answers are saved and checked; the measured result is no improvement in household question answering.

## Run in Colab

1. Open https://colab.research.google.com/ and upload one of the notebooks above.
2. For benchmarks choose a GPU runtime; for the class SLM RAG notebook use CPU. Run the cells in order.
3. In the first upload cell select `output/a7/hestia-a7-person2-colab.zip`. The archive is an explicit code/data allowlist, not a repository backup.
4. For RAG only, upload `/Users/darshan/Documents/Hestia/selected_baseline.pt` in the separate checkpoint cell. Its SHA-256 must be `ea5b43d934bed646d02183c50e371f89df57801cc1bc7ef45027ccb2d8de3f36`. The checkpoint is intentionally absent from the archive and ignored by Git.
5. Benchmarks load one model at a time using Transformers and checkpoint every response. Resume in the same environment; preserve raw errors. The environment sidecar prevents accidentally mixing different conditions. Colab storage is temporary: download partial evidence before disconnecting.
6. RAG preserves full prompts and records the model's actual last-32-character context. The original character tokenizer/context and weights remain unchanged. Retrieval can succeed while generation fails to use the fact; explain this using the exported evidence.
7. Review the raw responses. RAG needs an overall quality score, factual accuracy, relevance, unsupported-information flag and notes for every response. The review cell refuses to mark an incomplete assessment complete. Benchmark scores follow `a7/evaluation_rubric.csv`.
8. Download the evidence ZIP and **File → Download → Download .ipynb**. Return both executed notebooks and evidence. Keep raw and reviewed evidence separately. Do not upload model weights to GitHub.

## Benchmark condition and limits

Assigned models: `facebook/opt-125m`, `Qwen/Qwen2-0.5B-Instruct`, `HuggingFaceTB/SmolLM2-1.7B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3`.

The Colab notebook explicitly uses NF4 weights, FP32 compute/nonquantized layers, eager attention, CUDA, batch 1, greedy decoding and 220 generated-token limit. Native loading remains the shared runner's default. CPU/MPS cannot use this optional NF4 path. Actual bitsandbytes/CUDA compatibility must be established in Colab; local loader tests use mocks, not GPU inference. Do not treat quantized results as native FP16/FP32 or assume teammates used the same precision. Download and model-loading latency are excluded. Measured single-request throughput is not validated production serving capacity.

For comparable baseline/RAG/fine-tuning results, Persons 2 and 3 must use the same package versions, seed, CPU thread count and generation settings and compare pre-training baseline outputs. Class checkpoint verification alone cannot guarantee identical sampled responses across different PyTorch versions.

## Completed cost contribution and integration boundary

`a7/results/local_costs.csv` contains all 15 models × six traffic levels, with compute/storage itemization and explicit proxy capacities. The dated pricing and workload are in `cost_assumptions.json`; `a7/person2_analysis.ipynb` is the executed analysis. Rebuild with `python -m a7.person2.review_benchmarks` and `python -m a7.person2.local_costs`. See `HANDOFF.md` for integration. The earlier Colab setup ZIP is an inference setup bundle, not the final handoff package.
