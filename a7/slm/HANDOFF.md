# Selected SLM for Persons 2, 3 and 4

Person 1 has completed the baseline, five independent architecture runs, four
sampling temperatures and Part 1 analysis in `slm_experiments.ipynb`.
The underlying class architecture is unchanged; tests compare its Python AST
against the professor's original notebook.

## Get the same checkpoint

The selected file is `a7/slm/checkpoints/selected_baseline.pt`. It is deliberately
**not in Git**. Obtain this exact file privately from Person 1 and place it at that
path. Do not commit or submit weights. Alternatively, rerun the completed notebook
with the recorded package versions and CPU settings and compare its tensor-state
SHA256 with `results/selected_checkpoint.json`. Different environments may produce
different weights; if the state differs, use the exact shared file for comparison.

From the repository root:

```python
import json
import torch
from a7.slm.handoff import load_selected, generate, state_hash

torch.set_num_threads(2)
manifest = json.load(open('a7/slm/results/selected_checkpoint.json'))
model, vocab = load_selected()
assert state_hash(model) == manifest['state_sha256']
text = generate(model, vocab, 'students ', **manifest['generation'])
print(text)
```

Generation settings are seed 42, temperature .7, 100 new **characters**, CPU.
The loader returns a new model every call. `generate` returns prompt plus
continuation, just like the class function. For a response-only table use
`text[len(prompt):]`, consistently in every condition.

## Shared limitations and responsibilities

- Architecture: embedding 48, heads 2, layers 1, feedforward 192, context 32.
- Vocabulary: newline, space, period and lowercase letters except **q** and **z**.
  Digits, uppercase letters, question marks, colons, apostrophes and other symbols
  are absent. `generate` reports unsupported characters instead of silently
  dropping them. Choose compatible fictional facts/questions, or explicitly
  document identical normalization in all conditions; do not expand the model's
  vocabulary or embeddings.
- Only the last **32 characters** of an input reach the model for each prediction.
  Person 2 must report which retrieved information actually remains visible; a
  long prompt may discard every retrieved document. Do not enlarge the trained
  positional embeddings to hide this limitation.
- Person 2 supplies the knowledge base and five common questions, records the
  baseline and top-K 1/2/3/5 results, and verifies weights stay unchanged.
- Person 3 loads a fresh original checkpoint, uses Person 2's facts/questions,
  records the same baseline, then fine-tunes. Preserve original checkpoint;
  save changed weights under a different ignored filename.
- Person 4 compares the three conditions with the same questions/settings.
- The selected baseline has 32,523 parameters, trained for 1,000 updates on the
  original repeated class corpus. It generates imperfect text. Record failures
  honestly; do not insert factual answers from retrieval as model output.

## Reproduce Person 1

Use the project's Python environment with torch, numpy, pandas, matplotlib,
psutil, nbformat, nbclient, nbconvert and ipykernel installed.
Exact versions from the recorded run are in `results/environment.json`.
From the repository root:

```sh
venv/bin/python -m pip install -r a7/requirements.txt
venv/bin/jupyter nbconvert --to notebook --execute \
  a7/slm/slm_experiments.ipynb --inplace --ExecutePreprocessor.timeout=1200
venv/bin/python -m unittest a7.tests.test_slm_handoff -v
```

The notebook records results in `a7/slm/results`, checkpoints in
`a7/slm/checkpoints`, and corpus in `a7/slm/training_corpus.txt`. Rerunning replaces
these generated files. The corpus is the original twenty class sentences
repeated 100 times; do not mix the new RAG/fine-tuning facts into it.
