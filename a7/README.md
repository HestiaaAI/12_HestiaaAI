# Assignment 7 shared benchmark and Person 1 handoff

This folder is independent of the Django application. It contains the locked
experiment contract for both Assignment 7 submissions.

## Person 1 completed foundation

- `benchmark_contract.py`: the exact 15 A6 models, five fixed size categories,
  a balanced 4/4/4/3 member allocation, 25 Hestia prompts, and the 10-point
  manual evaluation rubric.
- `benchmark_runner.py`: deterministic local/Colab runner that records latency,
  output tokens, tokens per second, raw output, environment, and review fields.
- `review_results.py`: reproducible first-pass self-evaluation using the shared
  ten-point rubric. The review notes make each score auditable.
- `multi_model_system.ipynb`: shared notebook scaffold and Person 1 execution
  section. Other members should return CSV files rather than edit this notebook.
- `model_registry.csv`, `prompts.csv`, and `evaluation_rubric.csv`: reviewable
  copies of the shared contract.
- `tests/`: guards against roster, prompt, allocation, and result-schema drift.

Person 1 models are distributed across four size categories:

1. `distilbert/distilgpt2`
2. `HuggingFaceTB/SmolLM2-360M-Instruct`
3. `Qwen/Qwen2.5-1.5B-Instruct`
4. `microsoft/Phi-3.5-mini-instruct`

## Run Person 1's 100 evaluations

Use one machine for all four models so latency and throughput remain comparable.
A CUDA Colab runtime is recommended for Phi-3.5. Do not combine timings collected
on different hardware without labeling them separately.

```powershell
python -m pip install -r a7/requirements.txt
python -m a7.benchmark_runner --owner P1 --dry-run
python -m a7.benchmark_runner --owner P1 --device cuda \
  --output a7/results/person1_benchmark.csv
```

The runner checkpoints after every generation and resumes by default. After all
generations finish, populate the rubric fields and then inspect the raw output
beside every score:

```powershell
python -m a7.review_results a7/results/person1_benchmark.csv
```

The reviewer checks exact labels, required JSON shape, task-specific concept
coverage, clarity, and unsupported details. Its notes explain each score; Person
1 must still review those notes before treating the CSV as final. Keep failed
generations visible and rerun them under the same configuration.

## Assignment 2 SLM dependency

Person 1 must start from the professor-provided Week 7 SLM notebook. The required
notebook was not present in the repository or the local Week 6 script folders
when this foundation was created. Do not substitute a Hugging Face model or a
new Transformer implementation. Once the class notebook is available:

1. Copy it into `a7/slm/`.
2. Preserve the original baseline values and training corpus.
3. Run the five required architecture configurations from the assignment, each
   from a newly initialized model.
4. Select one trained checkpoint and use the same original checkpoint for RAG,
   fine-tuning, and the final comparison.
5. Run temperatures `0.2`, `0.5`, `1.0`, and `2.0` with unchanged weights,
   prompt, maximum output length, and random seed.
6. Record actual parameter counts, final loss, training time, and generated text.

Checkpoint files must be shared privately if needed and must never be committed.
The repository ignores `.bin`, `.safetensors`, `.pt`, `.pth`, `.ckpt`,
`a7/checkpoints/`, and `a7/model_cache/`.

## Team handoff rules

- Everyone uses these exact model IDs, prompts, output instructions, and rubric.
- Each member runs only the models assigned to their `owner` value.
- Do not edit another member's raw evidence.
- Return one CSV with all 25 rows per model and no duplicate model/prompt keys.
- Person 2 and Person 3 must still calculate their respective 90-row cost tables
  across all 15 models, regardless of their four-model benchmark allocations.
- Person 1 merges the four reviewed CSV files into the final notebook.
- Person 4 owns the five routing strategies and `system_design.md`.
