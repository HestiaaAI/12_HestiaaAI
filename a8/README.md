# Ask Hestia · Assignment 8

RAG over a fictional household handbook (chores, shopping, inventory, maintenance,
guest prep).

## Submission files

| File | Role |
|---|---|
| [rag_system.ipynb](rag_system.ipynb) | Full pipeline + 45-run experiments (saved outputs) |
| [rag_analysis.md](rag_analysis.md) | Evaluation tables, comparisons, failures, system design |
| [requirements.txt](requirements.txt) | Dependencies |
| This README | Setup and how to run the notebook |

## Setup

From the **repository root**:

```sh
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -r a8/requirements.txt
```

Keep `a8/data/` next to the code. Do not commit model weights; inference downloads
public Hugging Face snapshots on first use.

## Run the notebook

```sh
jupyter notebook a8/rag_system.ipynb
```

By default the notebook reads saved evidence under `a8/results/` (no download).
Set `RUN_INFERENCE = True` in the notebook only if you want a fresh run.

## Dataset (brief)

| Dataset | Paragraphs | Words |
|---|---:|---:|
| `full` | 30 | 2,901 |
| `small` (scaling) | 15 | 1,461 |

Chunkers: `fixed`, `overlap`, `hybrid`. Generator: `Qwen/Qwen2-0.5B-Instruct`.
Encoders: MiniLM (384), MPNet (768), BGE-large (1024).

## Canvas ZIP

Zip these four files from `a8/`:

```sh
cd a8
zip hestia-a8-submission.zip rag_system.ipynb rag_analysis.md requirements.txt README.md
```
