# Ask Hestia handbook foundation

Ask Hestia answers questions about a fictional household’s routines using a
shared handbook. The five Markdown documents cover chores, shopping, inventory,
maintenance reporting and guest preparation. They describe example household
policies and use invented data.

| Dataset | Selection | Paragraphs | Words | Fixed chunks | Overlap chunks | Hybrid chunks |
|---|---|---:|---:|---:|---:|---:|
| `full` | Both topics in each of the five documents | 30 | 2,901 | 30 | 20 | 20 |
| `small` | First topic in each document | 15 | 1,461 | 15 | 10 | 10 |

Full-corpus paragraphs range from 92 to 103 words. Blank lines separate prose
paragraphs. Headings label documents and topic sections. Source IDs use the
document filename and original paragraph number, such as `inventory-02`.
Keep the source paragraph order fixed once the experiments begin so source IDs
stay stable.

## Chunking strategies

| Strategy | Rule |
|---|---|
| `fixed` | Pack consecutive complete sentences into chunks with a 140-word target maximum. Start a new chunk before the next sentence would exceed the target. An oversized sentence stays whole. |
| `overlap` | Combine two adjacent paragraphs with a stride of one paragraph. For a three-paragraph topic the windows are P1 + P2 and P2 + P3. A one-paragraph topic produces a single chunk. |
| `hybrid` | Use the topic headings as semantic boundaries. Pack consecutive whole paragraphs within each topic to a 240-word target maximum. Preserve paragraph breaks and keep an oversized paragraph whole. |

All strategies reset at each topic boundary. Chunk records include the document,
topic, original paragraph IDs and full text. Fixed chunks can contain a portion
of a source paragraph, so use the actual text to check whether a fact is present.
The fixed splitter uses sentence-ending punctuation appropriate for this controlled
handbook. Revisit it before applying it to text containing abbreviations or complex
punctuation.

## Use from the shared notebook

Start Jupyter from the repository or extracted submission root with the `a8/`
folder available. The corpus module uses the Python standard library. Keep
`a8/data/` beside `a8/corpus.py` in the submission ZIP.

```python
from a8.corpus import load_chunks, load_queries

chunks = load_chunks(strategy="overlap", dataset="full")
evaluation = load_queries()
texts = [chunk.text for chunk in chunks]
query_texts = [item["query"] for item in evaluation]
```

The five fixed queries in `data/queries.json` include expected answers, required
facts, supporting paragraph IDs and verbatim evidence spans. Embed only the query
text and chunk text. Use the expected answers and evidence spans when evaluating
results. For every run, save the retrieved chunk IDs, full text, scores and source
paragraph IDs alongside the generated answer. A source ID match can identify a
candidate hit. Inspect the chunk text to see whether it contains the needed facts.

```sh
python -m a8.corpus --dataset full
python -m a8.corpus --dataset small
python -m a8.corpus --dataset full --output-dir a8/results/chunks
```

The main nine-configuration matrix uses `full`. For scaling, compare `small` and
`full` with the same queries, chunking strategy, embedding model, generator,
prompt, decoding and top-k. The larger corpus adds 15 paragraphs on neighboring
topics. Both datasets retain all five reference answers, and the chunks from the
retained topics keep their IDs and text. Measure whether the added documents change
ranking, answer quality or latency.

## Shared generator and 45-row experiment

Open [rag_system.ipynb](rag_system.ipynb) for the executed matrix. The [Person 3 handoff](person3/README.md) includes repeat instructions, the [quality rubric](person3/RUBRIC.md), and the [three-model comparison](person3/COMPARISON.md).

## Canvas submission package

Include the full `a8/` tree in the Canvas ZIP: the notebooks import its Python modules
and read its handbook and saved evidence. The files below need those supporting files
to run end-to-end after extraction.

| File | Role |
|---|---|
| [rag_system.ipynb](rag_system.ipynb) | Full implementation and experiments |
| [rag_analysis.md](rag_analysis.md) | Evaluation tables, comparisons, failures, system design |
| [system_design_diagram.png](system_design_diagram.png) | System design diagram referenced by the analysis |
| [requirements.txt](requirements.txt) | Dependencies |
| This README | Setup and how to run the notebook |

```sh
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -r a8/requirements.txt
jupyter notebook a8/rag_system.ipynb
```

By default the notebook reads saved evidence under `a8/results/` (no model
download). Set `RUN_INFERENCE = True` only for a fresh run. Do not commit model
weights; public Hugging Face snapshots download on first inference.

```sh
mkdir -p dist
zip -r dist/hestia-a8-canvas.zip a8 -x '*__pycache__*' '*ipynb_checkpoints*' '*.safetensors' '*.bin' '*.pt' '*.pth'
```

## Completed Person 2 evaluation and scaling

[Person 2's executed analysis](person2_retrieval_scaling.ipynb) contains the 15
small-model RAG rows and 10 paired scaling requests from the returned Colab run.
[Findings](person2/FINDINGS.md), [handoff](person2/HANDOFF.md) and full evidence in
`results/person2/completed-2026-11-09/` include actual answers, complete chunks,
reviewed quality/noise and measured end-to-end latency. Rebuild the tables with
`python -m a8.person2_analysis`. Reviews are AI-assisted; student signoff is not
recorded. These Colab timings are separate from the matched Person 3 Mac matrix.
