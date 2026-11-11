# Hestia AI — Team 12

Hestia is a household operations project for INFO 490: shared tasks, inventory,
shopping and an AI brain-dump workflow. This repository also contains the two
independent Assignment 7 research submissions. **Django is not needed to review
or run the Assignment 7 experiments.**

## Current submissions: Assignment 8 + Assignment 9

- **A9 Ask Hestia** (Django RAG at `/tasks/ask/`): setup below under
  [Assignment 9](#assignment-9--ask-hestia-current-django-ai-feature); AI docs in
  [README_AI.md](README_AI.md); demo [a9/person4/DEMO.md](a9/person4/DEMO.md).
- **A8 RAG package:** [a8/README.md](a8/README.md), analysis
  [a8/rag_analysis.md](a8/rag_analysis.md), Canvas ZIP on `dev-ag-a8-canvas-zip`.

Historical A7 research package (still complete for review):

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

## Assignment 9 · Ask Hestia (current Django AI feature)

Signed-in handbook Q&A at `/tasks/ask/`. Local MiniLM retrieval over the A8
overlap handbook chunks, then `Qwen/Qwen2-0.5B-Instruct` (A6/A7-tested). No paid
API is required for the primary feature.

| Doc | Path |
|---|---|
| AI workflow, model rationale, evaluation | [README_AI.md](README_AI.md) |
| Architecture | [a9/person4/ARCHITECTURE.md](a9/person4/ARCHITECTURE.md) |
| Evaluation evidence | [a9/EVALUATION.md](a9/EVALUATION.md) |
| Demo rehearsal (2 successes + 1 limitation) | [a9/person4/DEMO.md](a9/person4/DEMO.md) |
| Canvas submission PDF | [docs/a9-canvas-submission.pdf](docs/a9-canvas-submission.pdf) |

```sh
python manage.py test workflows.test_ask_hestia workflows.test_ask_hestia_views
python manage.py ask_hestia "Where does the shared cordless drill normally live?" "What is the capital of Australia?"
```

First Ask Hestia request downloads MiniLM and Qwen into `HF_HOME` (see
`.env.example`). Keep `.env` and model caches out of Git.

## Assignment 8 · RAG notebook package

See [a8/README.md](a8/README.md) and [a8/rag_analysis.md](a8/rag_analysis.md)
(Person 4 analysis uses Person 3’s 45-row matrix plus Person 2’s completed Colab
MiniLM evaluations under `a8/results/person2/completed-2026-11-09/`). Canvas ZIP
on branch `dev-ag-a8-canvas-zip`: `a8/hestia-a8-canvas.zip` (full `a8/` tree).


## Grocery tracking demo

Open **Groceries** after signing in with an active household membership. To
prepare two demo accounts, create or select a Workspace in Django admin and
add one active Membership for each account under that Workspace.

1. Add two milk batches with different expiry dates, one tomorrow and one next week.
2. Sign in as the second roommate and update one batch's quantity. Mark a batch
   consumed or discarded to move it to recent history.
3. On a batch expiring today or within three days, select **Suggest a meal**.
   The existing local Qwen model uses up to six eligible batches. Select
   **Approve and add to Tasks** to create a household-only task. A changed
   batch or expired draft requires generating a fresh suggestion.

The page evaluates dates in the household's timezone whenever it loads. Past-date
batches are listed separately and excluded from meal suggestions. The first model
request downloads the same Qwen checkpoint used by Ask Hestia, so warm it on
the demo machine before presenting.

To deploy this branch on the existing PythonAnywhere web app, use the web app's
virtualenv and deployment checkout. Update the checkout to `cn32-demo`, install
the dependencies, and run the following against the web app's database:

```sh
python manage.py migrate --settings=hestia_config.settings.production
python manage.py collectstatic --noinput --settings=hestia_config.settings.production
python manage.py check_grocery_expiry --settings=hestia_config.settings.production
```

Reload the web app from the Web tab. To run a daily expiry report on a host
with scheduling enabled, add this command to the host scheduler, substituting
the web app's actual paths and using the same environment as the web app:

```sh
/path/to/venv/bin/python /path/to/checkout/manage.py check_grocery_expiry --settings=hestia_config.settings.production
```

The scheduled check writes counts to the scheduler log. Roommates see the
current alerts inside Groceries. On PythonAnywhere, schedule availability depends
on the account. See [PythonAnywhere scheduled tasks](https://help.pythonanywhere.com/pages/ScheduledTasks/).

On **Groceries**, choose **Scan receipt** to read an English receipt photo and
review the resulting batches. Enter any missing quantities and storage locations,
then save. You can paste receipt text if the scanner is unavailable. The photo is
processed in the browser using Tesseract.js. **Use microphone** on the add or
edit form dictates the grocery name in browsers that support speech recognition.
