## Part 4: baseline, RAG and fine-tuning

Independent Windows retraining reproduces 4/5 fine-tuned continuations exactly; Q4 differs. The final state hash also differs from the Mac export. Weights change locally and loss ends at 0.2220. This verifies the training recipe with a cross-platform numerical limit, not byte-identical checkpoint reproduction. The table retains Person 3’s source continuations.

Preserve Person 2 baseline/RAG 1–10 reviews. Review fine-tuned continuations on the same 1–10 scale: 1 no correct answer, partial credit for correct but incomplete/contradictory answers, 10 fully correct without contradiction. Source phrase-match scores (including zeros) retained separately; not averaged with reviewed scores.

All 5/5 pre-training baselines match Person 2 exactly. Person 3 reports 10 examples and 300 training steps, loss 4.6915 → 0.2225; recorded training time 0.45 seconds on their machine. Original state `a8b4dcabc94e13e50afc0123b4198b8394a572bc425e8898858e35cbe571e700`; fine-tuned state `be99d1b3affe37cfe7c7bed57cd0f19bcdce91daaf7be85c54e48799483fcecb`. Baseline/RAG retain the original state; fine-tuning changes it. Timing is the supplied training-loop measurement, not end-to-end runtime.

Five questions are also present in fine-tuning examples; no held-out generalization claim. Single seed. Changed-state evidence is reported by Person 3; see independent reproduction report for local verification.

The original phrase-matching checker gives 10/10 to Q3 and Q4, although both continuations mix correct phrases with wrong facts. The final table uses the disclosed continuation-level review and flags unsupported information in all five tuned answers. Fine-tuning learns household wording but produces no wholly correct, contradiction-free answer in this set.

The table preserves actual exported continuations. Scores are assistant-assessed, not independent human grading. All three conditions are supplied.

RAG Top-K = 1, selected by highest mean factual accuracy with ties resolved by lower K. Selection uses these same five evaluation questions; this is descriptive, not held-out evaluation.

| Question | Baseline SLM | SLM + RAG | Fine-tuned SLM |
|---|---|---|---|
| Q1: when is laundry day. | the predicts probabmenters are use models and un learning res artifining paplications.<br>students crea | smalll learning res models preveows.<br>ingrametion learaning helps useful models models can learnung o | where are in the shed.<br>where is dish soap.<br>dish soap is under the hall.<br>spare bulbs are bulbs are gu |
| Q2: when is trash day. | the predicts probabilition paransmelld django application artificial intelligencers usefuse models l | the predicts probabilition paransmelld django application artificial intelligencers usefuse models l | when is laundry day is monday.<br>when is laundry day.<br>laundry day.<br>when is laundry day.<br>laundry day.<br>g |
| Q3: where are guest towels. | artificial inngual networks are pytok<br>stentraining hang helps artificial intelligencers artuage mode | artition use preversitity lon learnedicts artual ingaal networks learnedicts artificial inngerameter | guest towels are in the shed.<br>when is laundry day.<br>guest towels are are in the hall.<br>spare guest tow |
| Q4: where are spare bulbs. | attention rkeach.<br>trach.<br>traning he students useful softworks learne predicts artuage models can re  | students unenchartificial intelligencers context tokearmers.<br>the uning models previos.<br>startificial  | spare in the shed.<br>dish soap is under the shed.<br>when are in the hall.<br>spare guest towels.<br>guest towe |
| Q5: where is dish soap. | students expe models chartificial intelligencers con prevers artificial intelligencers.<br>attion usegr | the charaning parammechantion rkware python runing rametersing res.<br>trammechation rammechane canis.<br> | dish soap.<br>dish soap is under the shed.<br>dish soap is under the shed.<br>where are bulbs are in the hall |

| Condition | Mean factual accuracy /10 | Mean relevance /10 | Responses with unsupported information /5 |
|---|---|---|---|
| Baseline | 1.00 | 1.00 | 5 |
| RAG | 1.00 | 1.00 | 5 |
| Fine-tuned | 2.40 | 3.60 | 5 |

### Retrieval and context evidence

| Top-K | Mean factual accuracy /10 | Questions retaining every expected fact in the initial visible context /5 |
|---|---|---|
| 1 | 1.00 | 2 |
| 2 | 1.00 | 0 |
| 3 | 1.00 | 0 |
| 5 | 1.00 | 0 |

4/5 selected RAG continuations differ from baseline. A changed continuation does not establish factual improvement. Original checkpoint-state hashes match; only the final 32 prompt characters reach the model at its first prediction. Retain the exported prompts/order rather than rebuilding tied retrieval rankings with different NumPy/scikit-learn versions.

### Quality and consistency evidence

- Q1, Baseline: Unrelated fragments about learning and models; no laundry-day answer. Expected fact: monday. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q1, RAG: Unrelated fragments about learning and models; no laundry-day answer. Expected fact: monday. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q1, Fine-tuned: Does not answer Monday; talks about the shed and invents soap under the hall.
- Q2, Baseline: Unrelated fragments about probability, Django and models; no trash-day answer. Expected fact: friday. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q2, RAG: Unrelated fragments about probability, Django and models; no trash-day answer. Expected fact: friday. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q2, Fine-tuned: Does not answer Friday; repeats laundry/Monday instead of answering trash day.
- Q3, Baseline: Unrelated fragments about neural networks and training; no towel location. Expected fact: in the hall. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q3, RAG: Unrelated fragments about neural networks and training; no towel location. Expected fact: in the hall. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q3, Fine-tuned: Includes the correct hall location but also explicitly places guest towels in the shed. Partial credit only; contradictory and repetitive.
- Q4, Baseline: Unrelated fragments about attention, students and models; no bulb location. Expected fact: in the shed. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q4, RAG: Unrelated fragments about attention, students and models; no bulb location. Expected fact: in the shed. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q4, Fine-tuned: Begins with the partial correct phrase spare in the shed, then invents soap under the shed and mixes unrelated facts. Partial credit, not a clean answer.
- Q5, Baseline: Unrelated fragments about students, software or learning; no soap location. Expected fact: under the sink. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q5, RAG: Unrelated fragments about students, software or learning; no soap location. Expected fact: under the sink. Off-topic assertions/fragments are unsupported by this household knowledge base; this flag does not assert that every fragment is factually false.
- Q5, Fine-tuned: Recognizes dish soap but repeatedly gives the wrong location under the shed instead of under the sink.

Consistency here means the observed pattern across five questions. Single-seed runs do not measure stability across random seeds.

### Step 4.2 final analysis

1. Fine-tuned achieved the highest available mean factual accuracy (2.40/10) on these five questions. This small set does not establish general performance.
2. Fine-tuning is the approach that updates weights; baseline and RAG retained the original selected checkpoint state.
3. RAG is easier to maintain as facts change because knowledge documents can be updated without retraining model weights.
4. For a startup with frequently changing policies, retrieval is the maintenance-oriented choice, provided the model can use the retrieved context. Interpret this classroom SLM’s actual quality scores in light of its 32-character window.
5. RAG and fine-tuning can be combined: tune the model’s behavior and retrieve current facts at inference time. That combined condition was not tested here.