# Hestia AI — Team 12

Hestia is a household operations project for INFO 490: shared tasks, inventory,
shopping and an AI brain-dump workflow. This repository also contains the two
independent Assignment 7 research submissions. **Django is not needed to review
or run the Assignment 7 experiments.**

## Current submissions: Assignment 7

Start with the [submission guide](a7/SUBMISSION.md). It maps every requirement to
its notebook, supporting evidence and reproduction instructions.

| Submission | Primary deliverables |
|---|---|
| Multi-model benchmarking, costs and routing | [multi_model_system.ipynb](a7/multi_model_system.ipynb), [system_design.md](a7/system_design.md) |
| Class SLM, RAG and fine-tuning | [SLM notebook](a7/slm/slm_experiments.ipynb), [RAG notebook](a7/slm/person2_rag_colab.ipynb), [fine-tuning notebook](a7/person3/finetune_slm.ipynb) |

All **375 model/prompt evaluations**, both **90-row cost tables**, five routing
scenarios and the five-question baseline/RAG/fine-tuning comparison are present.
Part 4 is a Markdown section in the submitted SLM notebook. Saved outputs can be
read immediately; no account token or model download is required for review.

The results include weak and incorrect answers. These are actual experiment
outcomes; the analysis explains context limits, scoring judgments and the cost
assumptions. See [review provenance](a7/REVIEW_STATUS.md). Mixed CPU/MPS/CUDA and
quantization conditions do not establish a global speed ranking. The API costs
use one explicitly disclosed paid-model alternative, not 15 exact-model quotes.

### Verify or package A7

From the repository root, with your Python environment activated:

```sh
python -m pip install -r a7/requirements.txt -r a7/requirements-person2-rag.txt
python -m unittest discover -s a7/tests -q
python -m a7.package_submission
```

The last command creates `dist/hestia-a7-submission.zip` with an entry guide,
notebooks, code, evidence and checksums. It excludes checkpoints, caches, local
experiments and the Django application. Review the guide before uploading.

For Windows machines with limited memory, use one numerical-library thread:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
```

For a Unix-like shell: `export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`.
Full training/inference reproduction has additional requirements; follow the
[submission guide](a7/SUBMISSION.md). Do not rerun generation merely to display
saved results. Private SLM checkpoints are intentionally absent from Git and ZIPs.

## Django application

The application is separate from A7. Use Python 3.13 and the root requirements:

```sh
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`, set a local `SECRET_KEY`, then run:

```sh
python manage.py migrate
python manage.py seed_template_demo
python manage.py runserver --settings=hestia_config.settings.development
```

Open `http://127.0.0.1:8000/`. Sign up at `/accounts/signup/` and sign in for
protected task pages and private APIs. The current A5 authentication rules
supersede older A3/A4 public-access examples. Keep credentials in your local
`.env`; the tracked SQLite database is retained as earlier assignment evidence.

The local Hugging Face brain-dump setup and model requirements are documented in
[README_AI.md](README_AI.md). API keys are not required for reading A7 results.

## Earlier assignments and evidence

- [A6 shared prototype](llm-test/ai_prototype.ipynb), [A6 results](a6_results/) and [AI integration guide](README_AI.md).
- [A5 authentication guide](docs/a5-member-1-authentication.md).
- [A5 API and Vega-Lite handoff](docs/a5-member-3/README.md).
- [Earlier README and assignment walkthroughs](docs/history/README-before-a7.md).
- [Screenshots](docs/screenshots/README.md).

Earlier test counts and deployment checklists are historical records, not current
verification claims. No new cloud deployment is implied by the A7 submissions.
