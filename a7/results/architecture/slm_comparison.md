## Part 4: baseline, RAG and fine-tuning

The table preserves actual exported continuations. Scores are assistant-assessed, not independent human grading. Baseline and RAG evidence are integrated; Person 3’s fine-tuning results are not supplied.

RAG Top-K = 1, selected by highest mean factual accuracy with ties resolved by lower K. Selection uses these same five evaluation questions; this is descriptive, not held-out evaluation.

| Question | Baseline SLM | SLM + RAG | Fine-tuned SLM |
|---|---|---|---|
| Q1: when is laundry day. | the predicts probabmenters are use models and un learning res artifining paplications.<br>students crea | smalll learning res models preveows.<br>ingrametion learaning helps useful models models can learnung o | Pending fine-tuning evidence |
| Q2: when is trash day. | the predicts probabilition paransmelld django application artificial intelligencers usefuse models l | the predicts probabilition paransmelld django application artificial intelligencers usefuse models l | Pending fine-tuning evidence |
| Q3: where are guest towels. | artificial inngual networks are pytok<br>stentraining hang helps artificial intelligencers artuage mode | artition use preversitity lon learnedicts artual ingaal networks learnedicts artificial inngerameter | Pending fine-tuning evidence |
| Q4: where are spare bulbs. | attention rkeach.<br>trach.<br>traning he students useful softworks learne predicts artuage models can re  | students unenchartificial intelligencers context tokearmers.<br>the uning models previos.<br>startificial  | Pending fine-tuning evidence |
| Q5: where is dish soap. | students expe models chartificial intelligencers con prevers artificial intelligencers.<br>attion usegr | the charaning parammechantion rkware python runing rametersing res.<br>trammechation rammechane canis.<br> | Pending fine-tuning evidence |

| Condition | Mean factual accuracy /10 | Mean relevance /10 | Responses with unsupported information /5 |
|---|---|---|---|
| Baseline | 1.00 | 1.00 | 5 |
| RAG | 1.00 | 1.00 | 5 |
| Fine-tuned | Pending | Pending | Pending |

### Retrieval and context evidence

| Top-K | Mean factual accuracy /10 | Questions retaining every expected fact in the initial visible context /5 |
|---|---|---|
| 1 | 1.00 | 2 |
| 2 | 1.00 | 0 |
| 3 | 1.00 | 0 |
| 5 | 1.00 | 0 |

4/5 selected RAG continuations differ from baseline. A changed continuation does not establish factual improvement. Original checkpoint-state hashes match; only the final 32 prompt characters reach the model at its first prediction. Retain the exported prompts/order rather than rebuilding tied retrieval rankings with different NumPy/scikit-learn versions.

### Quality and consistency evidence

- Q1, Baseline: Assistant assessment of the supplied raw continuation: Unrelated fragments about learning and models; no laundry-day answer. Expected fact: monday. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q1, RAG: Assistant assessment of the supplied raw continuation: Unrelated fragments about learning and models; no laundry-day answer. Expected fact: monday. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q2, Baseline: Assistant assessment of the supplied raw continuation: Unrelated fragments about probability, Django and models; no trash-day answer. Expected fact: friday. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q2, RAG: Assistant assessment of the supplied raw continuation: Unrelated fragments about probability, Django and models; no trash-day answer. Expected fact: friday. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q3, Baseline: Assistant assessment of the supplied raw continuation: Unrelated fragments about neural networks and training; no towel location. Expected fact: in the hall. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q3, RAG: Assistant assessment of the supplied raw continuation: Unrelated fragments about neural networks and training; no towel location. Expected fact: in the hall. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q4, Baseline: Assistant assessment of the supplied raw continuation: Unrelated fragments about attention, students and models; no bulb location. Expected fact: in the shed. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q4, RAG: Assistant assessment of the supplied raw continuation: Unrelated fragments about attention, students and models; no bulb location. Expected fact: in the shed. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q5, Baseline: Assistant assessment of the supplied raw continuation: Unrelated fragments about students, software or learning; no soap location. Expected fact: under the sink. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q5, RAG: Assistant assessment of the supplied raw continuation: Unrelated fragments about students, software or learning; no soap location. Expected fact: under the sink. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.

Consistency here means the observed pattern across five questions. Single-seed runs do not measure stability across random seeds.

### Step 4.2 final analysis

1. Baseline, RAG achieved the highest available mean factual accuracy (1.00/10) on these five questions. A three-condition accuracy winner cannot be named until fine-tuning outputs arrive.
2. Fine-tuning is the approach that updates weights; baseline and RAG retained the original selected checkpoint state. No fine-tuned weights or outputs were supplied to verify that condition.
3. RAG is easier to maintain as facts change because knowledge documents can be updated without retraining model weights.
4. For a startup with frequently changing policies, retrieval is the maintenance-oriented choice, provided the model can use the retrieved context. Interpret this classroom SLM’s actual quality scores in light of its 32-character window.
5. RAG and fine-tuning can be combined: tune the model’s behavior and retrieve current facts at inference time. That combined condition was not tested here.