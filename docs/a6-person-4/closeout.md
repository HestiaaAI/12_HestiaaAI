# P4 closeout after the P3 merge

## Completed work

- The full Django suite passed 175 tests in 50.229 seconds. A separate Django
  system check reported no issues. The new larger-model benchmark harness also
  passed its five unit tests; those checks do not count as inference results.
- P4's input/review/edit/exclude/confirm/save flow uses Person 2's local service
  and the existing Task forms/model. No model or provider implementation replaced.
- README_AI.md now documents Person 3's implemented Groq feature, settings,
  saved-task URLs, explicit disclosure/POST, and preview-only behavior.
- The old optional pre-save callable is distinguished from the supported Groq
  service; its incompatible signature is not presented as a working Groq hookup.
- `workflows/test_ai_action_plan.py` covers the combined P4/P3 flow with CSRF
  enforced: no Task writes before confirmation, exclusion, server-owned creator,
  saved-task link, GET disclosure with no external call, explicit provider POST,
  and no plan-triggered Task changes.
- The real-local-model smoke check was rerun on an in-memory database using
  Qwen2-0.5B weights. It generated three suggestions, saved zero before
  confirmation, excluded one, and saved two edited tasks. It then exercised the
  actual Groq view/service with a mock HTTP response; no live key or paid call.
  Evidence: `a6_results/person4_django_integration.json`.
- All 24 P4 raw responses and criterion-score notes were read again. Scores and
  original timing/output evidence were retained. The review remains explicitly
  assistant-assisted; independent human approval is not asserted. Audit:
  `a6_results/person4_review_audit.json`.

## Visual QA: exact scope and blocker

The smoke script's `--visual-fixtures` option renders seven HTML states from the
real Django templates: input, generated review, missing-confirmation error,
successful save, saved task detail, Groq disclosure, and Groq plan preview.
These private snapshots live under ignored `.local-backups/p4-visual-qa/` with
local CSS/images and an explicit static-fixture label. Local model suggestions
are real; the external preview is a deterministic fixture. Hidden test session
tokens and local configuration are not committed.

Windows Computer Use was attempted in a separate Chrome window. The tool stopped
automation because it could not determine the current browser URL confidently
enough to enforce its policy. No further UI automation was attempted after that
stop. **Desktop/mobile visual inspection is not passed or completed.**

For the submitter's remaining manual visual check, open those snapshots locally
and inspect input/review/errors/success at desktop width and at a 390px responsive
viewport. For a live end-to-end demo, start Django, sign in with an active
household membership, generate/edit/exclude/confirm, open a saved task, then open
the action-plan disclosure. Submit to Groq only with private runtime configuration
and appropriate consent. The P3 evidence already documents its own live external
provider/browser verification; P4 does not relabel that as its own visual pass.

## Ownership boundaries

P4 has now supplied the missing one-large/three-above-10B candidates: 32 actual
Colab T4 generations with reviewed outputs. See [large-models.md](large-models.md).
Main PR #31 has since merged a different balanced category plan and final
notebook copies. Those are preserved; P1/the team decides whether to incorporate
the new larger-model evidence under the original ranges. The Windows encoding issue
in P3's benchmark helper remains with P3. This closeout does not alter those
files, fabricate human signoff, or claim the whole assignment is ready.
