# Person 3 · Shared generator and embedding experiment

The generator is `Qwen/Qwen2-0.5B-Instruct` at revision `c540970f9e29518b1d8f06ab8b24cba66ad77b6d`. The project recorded eight runs of this exact model in `a6_results/person4_benchmark_results.csv` and 25 in `a7/results/person2_benchmark.csv`. All three embedding encoders use the same generator, system instruction, ranked context format, greedy decoding and 128-token output cap. The three encoder revisions match Person 2’s smoke tests.

## View the work

Open `a8/rag_system.ipynb` for the executed notebook, or read `a8/person3/COMPARISON.md`. The 45-row `a8/results/person3/evaluation.csv` includes the full passages, generated answers, scores, timing and review notes. Filter the size column to medium for the 15 Person 3 rows. The other 30 rows are matched comparison runs by Person 3. All 15 small-model chunk rankings were checked against Person 2’s saved retrieval evidence.

Raw JSONL files include exact prompts, hit order, source paragraph IDs, similarities, token counts and timings. Each folder also includes model revisions and runtime details. AI-assisted grading decisions are in reviews.csv, tied to the query, output and retrieved chunks by a fingerprint; see RUBRIC.md. Students can inspect and revise these decisions.

## Run from the repository root

Use Python with the dependencies from `a8/person2/requirements.txt`. The recorded runs used Python 3.14 on an Apple Silicon Mac, CPU with four PyTorch threads. Install dependencies in an isolated environment:

```sh
python -m pip install -r a8/person2/requirements.txt
python -m a8.person3_analysis
```

The second command validates the saved review and rebuilds both CSV tables without downloading weights. The notebook uses the same saved evidence by default. Set its RUN_INFERENCE switch to True to also run fresh inference into `a8/results/repeat/`. For just one encoder:

```sh
python -m a8.person3_experiments medium --out a8/results/repeat/medium
```

The first inference run needs internet for public model weights. Later runs can use HF_HUB_OFFLINE=1 when the exact snapshots are cached. Use a fresh directory for new measurements. A partial run can resume on matching settings. If regenerated answers or contexts differ, review them before scoring. Never copy old scores onto changed outputs.

For Person 2’s small/full hybrid scaling comparison, the shared runner also accepts:

```sh
python -m a8.person3_experiments small --scaling --out a8/results/repeat/small-scaling
```

For Person 4’s improvement test, freeze the baseline generator and record any changed prompt, query or retrieval settings as a separate intervention. The comparison folder contains baseline evidence. Person 4 can extend the notebook with the failure analysis, design reflection and packaging.
