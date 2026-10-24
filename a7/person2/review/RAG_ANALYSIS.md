# Person 2 RAG results — response review

These findings are based on the 25 continuations in the user-supplied `person2_rag_evidence.zip`. Scores are an AI-assisted assessment, not independent human grading. Raw responses must remain unchanged and accompany the reviewed results in the final submission.

## Results

| Condition | Responses | Correct household answers | Mean quality | Mean accuracy | Mean relevance |
|---|---:|---:|---:|---:|---:|
| Baseline | 5 | 0/5 | 1/10 | 1/10 | 1/10 |
| Top 1 | 5 | 0/5 | 1/10 | 1/10 | 1/10 |
| Top 2 | 5 | 0/5 | 1/10 | 1/10 | 1/10 |
| Top 3 | 5 | 0/5 | 1/10 | 1/10 | 1/10 |
| Top 5 | 5 | 0/5 | 1/10 | 1/10 | 1/10 |

All outputs contain off-topic, often malformed fragments about models, training, students or software. None provides the requested day or household location. The unsupported-information flag means these continuations are not grounded in the household KB; it does not mean every generic assertion is provably false. A floor score of 1 follows the required 1–10 scale.

The intended document ranks first for all five questions. The K=1/2/3/5 lists have exactly the required number of documents and include the intended source. At higher K, rank-first-first packing leaves lower-ranked documents closer to the final question, so the original model's last-32-character crop often retains distractors instead of the intended fact.

The export reports identical original/final tensor-state hashes (`a8b4dcabc94e13e50afc0123b4198b8394a572bc425e8898858e35cbe571e700`) and uses CPU, two threads, seed 42, temperature 0.7 and 100 character tokens. This is consistent with a no-training RAG run; it is exported evidence, not an independent reexecution. Reported environment: Python 3.13.16, PyTorch 2.11.0+cpu, NumPy 2.1.3, scikit-learn 1.6.1, pandas 2.2.3.

## Required analysis answers

1. **Did providing retrieved information change the SLM's responses?** Yes: Top-1 changes the continuation for Q1, Q3, Q4 and Q5, while Q2 remains identical to baseline. These changes do not produce correct household answers.
2. **Did RAG improve factual accuracy?** No: all five baseline answers and all twenty RAG answers fail to state the expected fact. The reviewed factual-accuracy score remains 1/10 in every condition.
3. **Did retrieving more documents always improve the responses?** No: Top-1 and Top-2 produce identical continuations for all five questions; Q5 changes at Top-3, and Top-5 matches Top-3 for every question. No K setting gives a correct answer, so the experiment establishes no quality advantage from a larger K.
4. **How did the SLM's context-length limitation affect the results?** The last-32-character crop removes large portions of the retrieved text; for example Q1 Top-1 retains “is monday.” but Top-2 retains “is friday.” from a distractor. The full expected facts for the towel, bulb and soap locations are already cut off even at Top-1, limiting what the model can use.
5. **Why might RAG behave differently with a small character-level model compared with a larger pretrained language model?** This class SLM learned short character patterns from a small generic corpus and is not an instruction-trained question-answering model, so supplying facts does not ensure it can use them. A larger pretrained instruction model would generally have more learned language skills and a longer token context, but that comparison was not measured here.

## Submission status

The raw experiment has the required response counts and honest negative findings. Finish the Colab review-export cell using the supplied scores, paste these analysis answers into a Markdown cell, then download the executed notebook and reviewed evidence. The full Person 2 workload is still incomplete until the 100 HF benchmarks and 90 local-cost cases are completed and integrated with the team.

A context-budgeted prompt variant could be a useful additional experiment, but it must be saved separately, use unchanged weights and be shared with Person 3 before using it for the common baseline/fine-tuning comparison. Do not silently replace this recorded run or claim that it achieved effective grounded question answering.
