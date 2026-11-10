# Assignment 9 · Live demo readiness (Steps 4.2–4.3)

**Scheduled 1v1 demo time:** Thursday, 12 Nov 2026 · 8:30 AM · EDUC 333

## Prep

```sh
python -m pip install -r requirements.txt
cp .env.example .env   # SECRET_KEY set; HF_ASK_HESTIA_DEVICE=cpu
python manage.py migrate
python manage.py runserver --settings=hestia_config.settings.development
```

Sign in (page is `@login_required`). Open **Ask Hestia** → `/tasks/ask/`.
Cold start can take tens of seconds while MiniLM and Qwen download/load; warm
page requests in evaluation were ~8–12 s on CPU.

Stack to name: MiniLM + A8 **overlap** chunks + top-k=2 + Qwen2-0.5B — chosen from
A6/A7 and the completed A8 matrices (Person 2 Colab MiniLM + Person 3 Mac
cross-encoder), then confirmed on the A9 page eval.

## Rubric mapping (2 successes + 1 limitation)

From `a9/evaluation.csv` **overlap** phase (`expected_behavior_met=yes`):

| Role | Case | Why it counts |
|---|---|---|
| **Success 1 (content)** | **Q4** bathroom drip | Only handbook content case with 100% completeness and `expected_behavior_met=yes` after overlap |
| **Success 2 (guardrail)** | **G3** capital of Australia | Full pass: handbook abstention, no invented rule, no model call path needed |
| **Limitation** | **Q3** cordless drill | Retrieval can show blue hallway bin; generator invents green kitchen return bin |

Among Q1–Q5 after overlap, **no second fully correct content answer exists**
(Q1 33%, Q2 50%, Q3 25% misleading, Q5 20%). Person 4 therefore uses G3 as the
second success—assignment Part 4 asks for successful *cases*, including
graceful failure/abstention—not two perfect handbook answers. Optional extras:
G1 empty-field error, G2 501-character error (also `expected_behavior_met=yes`).

## Two successful cases

### Success A — Complete content answer (Q4)

> The bathroom tap has a slow drip even with the handle shut. How do I report it to our household?

Show the Plumbing / Maintenance-board answer with reuse, detail fields and
coordinator notification. Person 3 overlap evaluation: **100%** completeness,
expected behavior met. Point at the **Sources** section so reviewers see grounding.

### Success B — Graceful out-of-scope abstention (G3)

> What is the capital of Australia?

Expect: `I couldn't find an answer in the household handbook.` No invented chore
rule. Explains guardrails (threshold / no-context path).

Optional: blank submit or 501-character paste to show form errors before retrieval.

## One failure / limitation (Q3)

> I need the shared cordless drill this afternoon. Where do I find it, what do I log, and where does the kit go when I finish?

Show that retrieval can cite the blue hallway bin while the generator may invent
a second return location (**green kitchen bin** in the recorded A9 overlap run).
Same hallucination class as A8 Person 2’s MiniLM Colab `small`/hybrid/Q3 in
`a8/results/person2/completed-2026-11-09/`. This is a **generation hallucination
with evidence present**—honest limitation.

## Technical explanation checklist (all teammates)

During the 1v1, anyone should be able to answer:

1. Where AI enters: `workflows/ask_hestia_views.py` → `answer_question`
2. Which models: MiniLM + Qwen2-0.5B; overlap chunks from `a8.corpus`; top-k=2
3. How inputs are processed: form validate → retrieve → generate or abstain → render
4. Limitations: small generator, CPU latency, residual hallucinations (Q3 / green bin), incomplete lists (Q5); more handbook text alone did not fix quality in A8 scaling
5. Pre-deployment improvements: stronger generator or checklist prompt, keep retrieval; never auto-execute chores

## Talking track (~2 minutes)

Ask Hestia is Django RAG over our A8 handbook, not a general chatbot. We chose
Qwen from A6/A7, MiniLM because A8 retrieval was already saturated at 384-d, and
overlap chunking because it won on both MiniLM Colab and BGE Mac—and again on the
A9 page before/after. Demo: plumbing success, Australia abstention, drill
green-bin hallucination.

## Demo slot

- **Team:** 12 Hestia
- **Feature:** Ask Hestia (`/tasks/ask/`)
- **When / where:** Thursday, 12 Nov 2026 · 8:30 AM · EDUC 333
- **Repo:** https://github.com/HestiaaAI/12_HestiaaAI
