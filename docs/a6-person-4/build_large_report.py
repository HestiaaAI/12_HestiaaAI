"""Build the P4 evidence notebook only after 32 real, reviewed responses exist."""
from pathlib import Path
from statistics import mean
import nbformat as nb
from verify_large_results import verify

ROOT = Path(__file__).resolve().parents[2]
rows, metadata = verify(ROOT / "a6_results/person4_large")
assert all(r["quality_score_0_to_10"] and "E/T/P/C/F=" in r["review_notes"] for r in rows), "Finish explicit content review first"
lines = ["# P4 larger-model findings", "", "Actual CUDA inference on " + metadata["gpu"] + ". "
         "NF4 weights, FP32 computation/non-quantized modules, eager attention, "
         "220 new tokens maximum, greedy generation; Qwen3 thinking disabled.", "",
         "| Model | Runs | Schema valid | Mean generation | Mean reviewed quality |",
         "| --- | ---: | ---: | ---: | ---: |"]
for model in metadata["models"]:
    selected = [r for r in rows if r["model_id"] == model]
    lines.append(f"| {model} | {len(selected)} | {sum(r['schema_valid']=='True' for r in selected)}/8 | "
                 f"{mean(float(r['generation_seconds']) for r in selected):.3f} s | "
                 f"{mean(float(r['quality_score_0_to_10']) for r in selected):.3f}/10 |")
lines += ["", "| Model | Zero-shot quality | One-shot | Few-shot | Many-shot |",
          "| --- | ---: | ---: | ---: | ---: |"]
for model in metadata["models"]:
    scores = [mean(float(r['quality_score_0_to_10']) for r in rows
                   if r['model_id'] == model and r['shot_mode'] == shot)
              for shot in ('zero','one','few','many')]
    lines.append('| ' + model + ' | ' + ' | '.join(f'{s:.2f}' for s in scores) + ' |')
lines += ["", "Observed content limitations:", "",
          "- Falcon extracted the concerns consistently but often overstated tap/Friday urgency; its BD2 zero-shot JSON was truncated at 220 tokens.",
          "- Qwen2.5 produced concise, schema-valid outputs in every case. Guest preparation was often only MEDIUM; valid JSON still needs priority review.",
          "- Phi changed the required schema in both zero-shot cases, misclassified library returns, invented overdue status, and truncated all three example-based BD2 outputs. Its 3/8 schema rate is conditional on the same 220-token cap used for every model.",
          "- Qwen3 was schema-valid in every case but overstated leak urgency in early modes and under-ranked detector batteries in few/many-shot. More examples did not monotonically improve quality.",
          "", "Scores are assistant-assisted content judgments using extraction/types/priority/clarity/format "
          "(3/2/2/2/1). Inspect each raw response and its explicit criterion notes in the notebook. "
          "Independent human approval is not asserted.", "",
          "Load timing includes uncached downloads. Generation timing is CUDA-synchronized. "
          "GPU/quantized timing cannot be treated as a controlled speed comparison against the "
          "earlier CPU/native measurements or a remote paid API.", "",
          "These candidates cover one large and three above-10B positions under the original ranges. "
          "Main PR #31 now uses different balanced bands and retains the earlier small-model selection. "
          "P1/the team owns whether to retain that plan or consolidate this larger-model evidence; "
          "do not blindly concatenate both P4 sets. See large-models.md for the exact handoff.", ""]
(ROOT / "docs/a6-person-4/large-model-findings.md").write_text("\n".join(lines), encoding="utf-8")

cells = [nb.v4.new_markdown_cell("""# Hestia P4 — larger-model evidence and review

This notebook reads **32 actual Colab GPU generations**, without rerunning inference.
Use `person4_large_models_colab.ipynb` to reproduce the model runs. The evidence
includes fixed shared prompts, model revisions/configuration, raw outputs, timing,
schema validation, and assistant-assisted content reviews. Earlier small-model
experiments remain separate. P1 owns the final 15-model notebook and category plan.
"""), nb.v4.new_code_cell("""from pathlib import Path
import importlib.util, json
import pandas as pd
from IPython.display import display, Markdown
ROOT=Path.cwd()
if not (ROOT/'manage.py').exists():
    ROOT=ROOT.parent
spec=importlib.util.spec_from_file_location('verify_p4_large',ROOT/'docs/a6-person-4/verify_large_results.py')
checker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
rows, metadata=checker.verify(ROOT/'a6_results/person4_large')
results=pd.DataFrame(rows)
results['generation_seconds']=pd.to_numeric(results['generation_seconds'])
results['quality_score_0_to_10']=pd.to_numeric(results['quality_score_0_to_10'])
assert len(results)==32 and results['quality_score_0_to_10'].notna().all()
print(json.dumps(metadata,indent=2))
"""), nb.v4.new_code_cell("""display(Markdown((ROOT/'docs/a6-person-4/large-model-findings.md').read_text(encoding='utf-8')))
display(results[['model_id','input_id','shot_mode','generation_seconds','schema_valid','quality_score_0_to_10']])
"""), nb.v4.new_code_cell("""for row in rows:
    print('\\n'+'='*80)
    print(row['model_id'],row['input_id'],row['shot_mode'])
    print('Seconds:',row['generation_seconds'],'Tokens:',row['output_tokens'],'Schema:',row['schema_valid'])
    print('Validation:',row['validation_errors'] or 'Passed shared schema')
    print(row['raw_output'])
    print('Quality:',row['quality_score_0_to_10'],'/10')
    print(row['review_notes'])
"""), nb.v4.new_code_cell("""display(Markdown((ROOT/'docs/a6-person-4/large-models.md').read_text(encoding='utf-8')))
display(Markdown((ROOT/'docs/a6-person-4/local-vs-api.md').read_text(encoding='utf-8')))
""")]
notebook = nb.v4.new_notebook(cells=cells, metadata={"kernelspec": {
    "name": "hestia-p4", "display_name": "Hestia P4", "language": "python"}})
path = ROOT / "llm-test/person4_large_results_review.ipynb"
nb.write(notebook, path)
print(path)
