# Step 2.3 · Does a larger embedding improve Hestia's answers?

These are matched runs of five handbook questions under fixed, overlap and hybrid chunking. Only the embedding encoder and its specified query formatting vary within a matched query/strategy comparison. The full corpus, top three, generator, prompt format, greedy decoding, output limit and CPU thread count are fixed. Each mean gives each of the 15 rows equal weight. Scores are on a 0–100 scale under the shared rubric.

| Embedding model | Dimensions | Runs | Evidence coverage | First supporting hit at rank 1 | Mean answer quality | Median retrieval | Median full request |
|---|---:|---:|---:|---:|---:|---:|---:|
| all-MiniLM-L6-v2 | 384 | 15 | 100% | 15/15 | 37.44 | 9.1 ms | 4.73 s |
| all-mpnet-base-v2 | 768 | 15 | 100% | 15/15 | 33.33 | 27.8 ms | 4.11 s |
| bge-large-en-v1.5 | 1,024 | 15 | 100% | 15/15 | 41.89 | 84.5 ms | 3.49 s |

**Retrieval quality.** For every encoder, the first hit referenced a supporting paragraph ID, and the three passages together contained every required quote. A fixed-length chunk can contain only part of a paragraph. Inspecting the first hit alone, it contained all required quotes on 11/15 small, 10/15 medium and 10/15 large requests. On the fixed grocery question, the first hit contained none of the required quote for all three encoders. With these five questions there was no measurable gain in those two retrieval metrics from increasing dimension. The identities of later passages could still change. Those passages are part of the generator's input.

**Answer quality.** BGE had the highest mean, while MPNet scored below MiniLM. On the out-of-stock question with overlapping chunks, the small encoder's answer just said to record the quantity. The medium and large runs both said to leave the original item unchecked and write “Out of stock,” earning 100. With fixed chunks on the same question, all three scored zero despite retrieving the rule. The prompt and raw passages for each case are in the JSONL files.

**Did larger always win?** No. On the kitchen handoff with fixed chunks, the small run scored 66.67, the medium 0 and the large 33.33. For preparing a guest room with hybrid chunks, all three covered every required fact. Embedding dimension alone cannot explain these observations: the encoders differ in training, and the generator can overlook or misuse evidence. The 128-token cap was reached on 11 of 45 requests; the reviews score only what the model actually returned.

**Latency.** Median retrieval latency grew with encoder size on this CPU. End-to-end medians did not follow the same order. The full request includes variable-length generation. There is one timing per configuration/query after warm-up, models were run in sequence, and five questions from one handbook are insufficient to establish a general speed or quality ranking.

The per-answer scores are an AI-assisted review of actual generated text. The matched facts, deductions, review notes and evidence fingerprints are in results/person3/reviews.csv. The full evaluation table includes the retrieved texts and actual end-to-end latency for each request.
