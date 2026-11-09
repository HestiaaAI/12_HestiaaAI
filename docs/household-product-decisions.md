# Phase 1B route and feature decisions

Product path: account sign-in → Household selection → Tasks → detail/action plan, approved AI drafts, Insights and CSV. This supersedes Phase 1A's assignment-compatibility contract.

| Surface / helper | Observed consumer | Decision |
|---|---|---|
| Account/allauth/admin/provider callback routes | Authentication, verification, administration | Retain unchanged |
| Board/detail/household selection/Home | Primary household experience | Retain |
| AI draft HTML and task-plan HTML | Board/detail actions, human approval | Retain and test real browser path |
| Product catalogue HTML / comparison helper | Secondary board action | Retain internal Products/Entries/Tasks scope and upstream error handling |
| CSV | Insights download | Move to `/tasks/export.csv`, `workflows:task-export-csv`; retain serialization/formula safeguards |
| Four task list aliases, standalone GET/POST search | Compatibility only after Phase 1A | Remove routes/functions/modules; board already filters/creates |
| Reports/statistics redirect pages | Compatibility only | Remove; Insights is canonical |
| Vega landing/spec/images; public sample JSON; creation JSON | Assignment demos, no product consumer | Remove routes/modules/templates and date-only aggregation |
| Task-list JSON, task-plan JSON, brain-dump JSON, catalogue JSON, response demo | No retained client; catalogue's technical API link is assignment copy | Remove transport adapters; keep domain logic used by actual HTML pages. CSV remains private 401/409 data boundary |
| Priority PNG | Insights image | Measure before deciding in Task 2; retained temporarily under existing private image path |
| Assignment seed/preview/demo commands | `forms_demo`, preview-only tests, history/docs | Remove runtime scripts and command; use synthetic test fixtures |
| Bundled handbook | Board secondary help; imports `a8.corpus` | Remove UI/route/service in Task 3; no product retrieval claim or research runtime dependency |
| Optional breakdown hook | Draft review UI/config `.env.example`; no bundled configured implementation | Keep bounded optional hook because current review workflow supports it; no provider added |
| Research folders/notebooks/assignment docs | Research tooling and tests only after handbook removal | Retain committed research as historical tooling, exclude from product release archive; no data/output deletion |

Audit included root/included URLconfs, templates/reverse lookups, imports, settings allowlists, management scripts, `import_string` hooks, `.env.example` and supported tests. No live external client/configuration was found for the removed internal JSON routes. These are intentional 404 removals, not compatibility redirects. `api/external.py` remains a real catalogue domain helper despite its directory name; it is not an exposed API.

Tests for old schemas/view-style/redirect/sample requirements are intentionally retired. Equivalent product security/escaping/CSRF/read-only/provider-error tests run on the board, HTML plan/draft/catalogue, Insights and canonical CSV; explicit route tests require removed transports to stop resolving. Detailed deleted-test mapping is in the verification report.
