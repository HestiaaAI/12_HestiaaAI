# Person 2 retrieval findings

CPU run on November 8, 2026. Small model: `sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions, k=3. These are retrieval findings; generated answers, shared quality ratings and end-to-end RAG latency are pending.

## Main matrix

All 15 matrix rows achieved source recall@3 = 1.0, source reciprocal rank = 1.0 and exact supporting-quote coverage = 1.0. Each strategy recovered the answer evidence within its top three chunks. This ceiling on five controlled queries does not establish equal performance on harder questions or equal answer quality. Full retrieved text and cosine scores are preserved in the raw JSONL.

## Scaling comparison

Fixed configuration: small model, hybrid chunking, k=3 and the same five queries. All answer evidence remains in the smaller dataset. The larger dataset adds 15 paragraphs of neighboring topics; it is a distractor experiment, not a missing-answer test.

| Dataset | Paragraphs | Words | Chunks | Raw vector bytes | Build ms | Median warmed retrieval ms | Range ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| small | 15 | 1461 | 10 | 15360 | 223.27 | 4.90 | 3.64–14.55 |
| full | 30 | 2901 | 20 | 30720 | 424.66 | 4.84 | 3.54–18.01 |

Each timing distribution has 50 observations (10 repeats × five queries), interleaved between datasets. The small timing difference is run variability, not evidence of a meaningful speed advantage. Vector bytes exclude text, JSON, model weights and compression overhead. Build times are one observation per index, not repeated benchmarks.

Both datasets retain perfect top-three evidence coverage and the supporting source remains at rank one for all five queries. Lower-ranked chunk IDs change for Q1, Q2, Q3 and Q5; Q4 keeps the same three IDs. Added-topic chunks enter the full-dataset results in four queries. This shows competition from neighboring topics without loss of the reference evidence.

Noise cannot be inferred from source IDs alone: related context may be useful, while a chunk from the expected source may add redundant material. A shared-rubric context relevance/noise review is still needed. No observed effect on generated answer quality can be claimed yet.

## Limits and next steps

- Longest small-model chunk: 233 tokens, within the standard 256-token limit. No chunk was silently truncated.
- Five queries and 10 versus 20 hybrid chunks are too small to establish production-scale search performance.
- Query encoding dominates such a tiny index; vector-memory growth is linear here.
- Keep the same generator/prompt/decoding across all team experiments and complete the 15 answer and quality fields with actual outputs.
- Model families differ in training and architecture; cross-model results must not attribute every difference to embedding dimension.
