# Run Person 2's remaining experiments in Google Colab

1. Open https://colab.research.google.com/ and upload `a8/person2_colab.ipynb`.
2. Use a **CPU runtime** (Hardware accelerator: CPU). The shared team
   generator is frozen to float32 CPU with four PyTorch threads; no GPU is required
   or used by this notebook. Hosted resources and availability are not guaranteed.
3. Run the setup cell, then upload `a8/results/person2/completed-2026-11-09/input_bundle.zip` when the
   notebook requests the input bundle. It contains only required A8 code, fictional
   handbook data, the shared rubric and model revision metadata, not weights/secrets.
4. Run the matrix cell (15 requests), then the scaling cell (10 requests). The same
   Qwen2-0.5B generator revision, prompt, greedy decoding, 128-token cap, small encoder
   revision, k=3 and four threads are used throughout. Each completed response is
   checkpointed immediately. The notebook uses Person 3's runner unchanged.
5. Download the evidence ZIP after each experiment; it also exports partial evidence
   if a run raises an error. Colab storage is temporary. Same-runtime reruns resume
   matching saved rows; different settings require a new run directory.
6. At the end, download `hestia-a8-person2-colab-evidence.zip` and use **File → Download
   → Download .ipynb** to save the executed notebook. Return both files for a new review; new answers must not inherit old scores.

The final check requires exactly 15 matrix and 10 scaling responses. Outputs include
full prompts, retrieved chunks, similarity scores, answers, token counts, actual
end-to-end request latency and runtime manifests. Loading/indexing/warm-up/grading
are excluded from request timings. No answer key is sent to either model.

The notebook creates an explicitly unreviewed answer table and review template;
it does not invent fact matches, unsupported-claim deductions or relevance ratings.
`a8/person2_analysis.py` rejects incomplete/changed evidence and missing reviews.
The November 9 hosted run completed all 25 requests with no saved notebook errors.
Its unchanged returned notebook is `a8/person2_colab_executed.ipynb`; completed
reviews and exported tables are in `results/person2/completed-2026-11-09/`.

Use the notebook and bundle together from the same build: the upload cell checks
its full SHA-256 before extraction. The installation keeps Colab's supplied torch
and NumPy, pins the embedding/Transformers stack, and records actual versions in
both experiment manifests. Fresh Colab measurements are not pooled with earlier
Mac latency measurements.
