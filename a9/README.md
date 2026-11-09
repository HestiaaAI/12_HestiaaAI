# Assignment 9 Person 3 evaluation

This evaluates the signed-in Ask Hestia page with real local models. Five handbook questions and three validation/abstention cases were sent through the Django test client with CSRF enforcement, authentication, form validation, the actual backend, and template rendering. A disposable in-memory SQLite database holds the synthetic evaluation account.

## Read the results

- [Evaluation and failure analysis](EVALUATION.md)
- [All 16 scored requests](evaluation.csv)
- [Fixed inputs and expected behavior](inputs.json)
- [AI-assisted review decisions](reviews.csv)
- [Baseline requests](results/baseline/requests.jsonl) and [overlap requests](results/overlap/requests.jsonl)

Each request includes the visible result, HTTP status, form errors, total page-request latency and diagnostic traces from actual inference. Traces retain sources, exact prompts, raw decoded text and token counts. HTML files preserve the rendered responses. Model-call wrappers delegate to the real functions. The before and after service sources are archived as backend.py.txt in their result folders.

Correctness is **required-fact completeness**, with one equal point for each fully conveyed required fact and no partial credit within a compound fact. It does not subtract for hallucinations. Usefulness and review notes separately flag false or misleading instructions. The expected-behavior column requires the complete correct response without material misinformation. Thus a partially correct but misleading answer cannot count as a successful answer. Guardrail cases are pass/fail against the specified expected behavior. Scores are AI-assisted judgments.

The recorded local run used CPU, four PyTorch threads and the application's native bfloat16 generator precision. It loaded models and warmed one request before recording the suite. Request latency includes Django handling, retrieval, generation and HTML rendering; the manifest separately records startup/warm-up time. These measurements are distinct from A8's float32 notebook runs.

## Repeat from the repository root

Follow the project's README to install requirements and configure the local environment. The feature uses Qwen/Qwen2-0.5B-Instruct and all-MiniLM-L6-v2. Initial model downloads require internet. No paid service is used by this evaluation.

~~~sh
python -m a9.analyze
python -m a9.evaluate --phase repeat-overlap
python -m a9.evaluate --phase repeat-baseline --baseline
~~~

The first command validates reviewed evidence fingerprints and regenerates the comparison CSV. The second measures the current service. The third loads the archived baseline service and connects it to the same actual Django view in process. Select a new phase name for each run; existing measurements are preserved. If model snapshots are cached, HF_HUB_OFFLINE=1 can be set before inference.

The script uses an in-memory database and requires migrations, so use a fresh Python process. Regenerated outputs can differ across runtime versions. Review new outputs before attaching scores. The reference reviews apply only to the saved before/after evidence.

## Handoff to Person 4

The evaluated intervention changes fixed sentence-packed chunks to two-paragraph overlapping chunks. Top-k remains two, similarity threshold 0.30, the generator and prompt remain the same, and the output cap remains 128 tokens. A regression test verifies the index uses the overlapping chunks and retains the shopping rule.

Use EVALUATION.md and evaluation.csv for steps 3.1–3.4 and integrate their findings into README_AI.md. One of five full handbook answers passed after the intervention; three guardrail cases passed in both phases. The complex drill answer still hallucinates a location. Before choosing two successful content examples for the live demo, verify the selected questions in the current app.

## Person 4 notes (appended)

Person 4 integration is under [person4/](person4/): architecture diagram, README_AI
append, demo rehearsal and Canvas PDF.

**Demo selection locked:** Success Q4 (only fully correct content case after
overlap), Success G3 (abstention; second measured pass), Limitation Q3 (green-bin
hallucination). See [EVALUATION.md](EVALUATION.md) Person 4 note and
[person4/DEMO.md](person4/DEMO.md). Re-verify in a signed-in browser before
Thu 12 Nov 2026 · 8:30 AM · EDUC 333; cold CPU loads remain slow.
