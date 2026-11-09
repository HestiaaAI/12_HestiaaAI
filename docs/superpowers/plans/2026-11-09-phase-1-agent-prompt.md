# Phase 1 delegation prompt

You are the senior Django engineer implementing Phase 1 of Hestia's demo preparation. Your assignment is to complete household isolation, consolidation of scattered assignment implementations, and a shared active-household context across the existing application. Deliver working code, regression tests and a teammate integration contract. Do not stop at a proposal or a resolver helper.

## Read first

Working directory: /Users/darshan/Documents/Projects/12_HestiaaAI-household-demo
Planning branch: household-onboarding-demo-plan

Read applicable AGENTS.md files, then:
- docs/superpowers/plans/2026-11-09-household-phases.md — authoritative phase order, interfaces, error semantics, task steps and acceptance gates.
- docs/superpowers/plans/2026-11-09-household-onboarding.md — backend review and broader feature context; its older implementation order is superseded.

Inspect actual current code and git state before changing anything. Base review was commit 421b75d; code may have moved. Use superpowers:executing-plans and test-first implementation. Execute directly; do not spawn subagents, add collaborators/reviewers/assignees, or add Co-authored-by/AI attribution. Preserve configured Git identity. Never include codex in a branch name. Create branch household-isolation from the planning branch if not already on a suitable execution branch; preserve unrelated work. Do not push, open a PR or deploy in this assignment.

## Product outcome

Roommates need one coherent household experience. A selected household must control task lists, details, creation, search, APIs, reports, exports, product lookup and AI task workflows. The selected household shown in navigation must match the data on every page. A household selector without actual query/write isolation is a failed deliverable.

Reuse Django sessions/allauth and existing Workspace/Membership. Display Household in product copy. No new dependency, auth system, duplicated Household model or visual redesign. Targeted consolidation of assignment-driven duplication is explicitly in scope. The UI teammate owns styling; provide stable names, form fields, context and useful semantic empty/error states.

## Implement these four tasks in order

1. Shared context and selection. Add households/context.py, context processor and middleware wiring with the exact proposed interfaces in the phased plan. Revalidate active membership on every request. No active memberships → useful onboarding state; one → auto-select; multiple without valid selection → picker. Add login-protected GET onboarding/picker and CSRF-protected POST switch. Invalid choice is 400 with no session mutation; GET switch is 405. Publish active_household, active_membership, household_memberships and can_manage_household. Preserve account/OAuth/verification/static/admin accessibility.

2. Task access. Scope every list/search/detail/create variant to selected workspace before applying user filters. Foreign details return 404 even if the user also belongs to that other household. Reject forged workspace fields and derive workspace/creator server-side. No membership means no reads or writes; never silently save with null creator. Preserve ReviewTaskForm inheritance when changing form constructors.

3. Secondary surfaces. Scope APIs, JSON/CSV downloads, summaries, chart specifications/images and internal product/shopping/task lookup. Pass scoped inputs into helpers; fix every call site. All public priority-chart variants use fixed fictional data at existing URLs/schema, never aggregate real households. Private response caching must not mix users/households. Document intentional changes to old assignment expectations; update fixtures rather than weakening security tests.

4. AI access and handoff. Validate active selected workspace before task-plan generation and brain-dump confirmation/save; recheck membership when persisting. Unauthorized requests must not call a provider or write data. Preserve signed drafts and human approval. Ask Hestia's bundled handbook is not household-aware retrieval: document its actual source and distinguish stateless extraction from data-bearing flows. Write docs/household-access-contract.md with a complete resolved-route matrix, status behavior, UI context, and rules future grocery/expense features must follow.

## Required behavior

- Anonymous private HTML retains login redirects; anonymous private data retains its 401 JSON boundary.
- Signed-in HTML without context redirects to onboarding/picker; household-dependent JSON/export/chart data returns 409 with error Select a household to continue. and code household_required.
- Foreign object 404; insufficient privilege within selected household 403.
- Removed/inactive members lose access next request, including stale sessions and staged AI drafts.
- Staff gets no application bypass outside Django admin.
- Nullable historical membership.user never grants access.
- Switching household changes all connected module data consistently.
- GET never changes household selection or household records.

## Tests and proof

Follow the phased plan's four red/green/commit cycles. Build independent A/B households, active/inactive/unaffiliated users and one dual member. Assert exact visible data and database writes, not status codes alone. Use distinctive names, priorities and dates so aggregate leaks are detectable. Cover anonymous, zero-membership, selected/unselected, stale selection, forged object IDs, cross-household writes, CSV/JSON, chart aliases and provider-call prevention. Test CSRF with enforcement enabled. Include review-form subclass compatibility and membership removal between preview and save.

Inventory every application URL and helper, including home, old demo routes, chart aliases and exports. Every household data route must have a documented policy and test. Future unimplemented inventory/expense CRUD receives the shared contract, not invented features.

Run baseline before edits and after changes:
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test households workflows api reports analytics
git diff --check

Use existing Python environment and explicit local test configuration; never copy real .env/database into this checkout or expose secrets. No AI downloads or live provider calls. Record baseline failures separately; fix phase-relevant defects, and report genuinely unrelated blockers without hiding/skipping tests or claiming full success. If PostgreSQL or browser proof is unavailable, say so explicitly.

## Stop condition and report

Finish only Phase 1. Do not build household creation, invitations, member lifecycle, grocery expiry, Splitwise, task recurrence, PWA/native packaging or deployment. Those belong to later phases/teammates.

Return: implemented behavior, commits/files, completed route matrix, actual test commands/counts/results, manual verification performed, known limitations and anything that blocks the acceptance gate. Report remaining later-phase work separately. The gate is satisfied only when existing data-bearing features consistently enforce active household isolation and the regression suite proves it.


## Expanded mandatory Phase 1 assignment: consolidate the experience

The user explicitly added removal/consolidation of isolated assignment services and functions to Phase 1. Read the “Phase 1 scope expansion — retire assignment fragmentation” and Task 5 sections in the phased plan and implement them after tasks 1–4. This is part of the completion gate, not a later suggestion.

Deliver one canonical task board with integrated search/create, contextual AI drafting, task detail/action-plan and one insights destination. Selected-household Home leads to that board. Household selection persists across the journey. Replace top-level assignment/demo links with Tasks and Household; add Groceries/Expenses only when actual features exist. Keep product lookup as a secondary catalogue tool and sample-handbook help accurately labeled.

Inventory callers/configuration before deleting code. Merge four separate list implementations and standalone search into the canonical workflow; old GET URLs become safe thin redirects and POST search remains read-only. Consolidate overlapping report aggregation behind explicit scoped query inputs. Share draft extraction/validation between HTML and JSON adapters while preserving their response contracts, provider behavior and review-before-save flow. Distinct model runtimes, task-plan generation and handbook retrieval do not become one generic AI service. Remove only proven-unused production wrappers/templates; preserve historical assignment artifacts.

Add failing unified-journey, legacy alias, shared-helper/schema, household context, provider-failure and product-copy tests before restructuring. Document every keep/merge/remove/alias decision and its replacement. Hiding links alone does not satisfy the assignment. A full rewrite, new AI abstraction framework or deleting useful features also fails it.

Final report must demonstrate both isolation and consolidation: canonical route map, removed/merged handlers/functions with replacement, remaining intentional adapters, real test evidence, and signed-in browser checks actually performed. Stop before household creation/invitations and other later phases.
