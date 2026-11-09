# Assignment 9 · Live demo readiness (Steps 4.2–4.3)

**Scheduled 1v1 demo time:** Thursday, 12 Nov 2026 · 8:30 AM · EDUC 333

## Prep

```sh
python -m pip install -r requirements.txt
cp .env.example .env   # SECRET_KEY set; HF_ASK_HESTIA_DEVICE=cpu
python manage.py migrate
python manage.py runserver --settings=hestia_config.settings.development
```

Sign in with a verified account that has an **active household membership**.
Open **Ask Hestia** → `/tasks/ask/`. Cold start can take tens of seconds while
MiniLM and Qwen download/load; warm requests in evaluation were ~8–12 s on CPU.

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
a second return location (green kitchen bin in the recorded overlap run). This is
a **generation hallucination with evidence present**—honest limitation.

## Technical explanation checklist (all teammates)

During the 1v1, anyone should be able to answer:

1. Where AI enters: `workflows/ask_hestia_views.py` → `answer_question`
2. Which models: MiniLM + Qwen2-0.5B; overlap chunks from `a8.corpus`
3. How inputs are processed: form validate → retrieve → generate or abstain → render
4. Limitations: small generator, CPU latency, residual hallucinations (Q3), incomplete lists (Q5)
5. Pre-deployment improvements: stronger generator or checklist prompt, keep retrieval; never auto-execute chores

## Talking track (~2 minutes)

Ask Hestia is Django RAG over our A8 handbook, not a general chatbot. We chose
Qwen from A6/A7 local tradeoffs and overlap chunking from A9 evaluation. Demo:
plumbing success, Australia abstention, drill hallucination.

## Demo slot

- **Team:** 12 Hestia
- **Feature:** Ask Hestia (`/tasks/ask/`)
- **When / where:** Thursday, 12 Nov 2026 · 8:30 AM · EDUC 333
- **Repo:** https://github.com/HestiaaAI/12_HestiaaAI
