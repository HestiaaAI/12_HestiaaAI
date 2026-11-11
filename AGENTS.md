# Hestia integration instructions

Before merging, rebasing, porting a feature, resolving a conflict, or changing shared routes/models/settings/templates, read [docs/TEAM_MERGE_GUIDE.md](docs/TEAM_MERGE_GUIDE.md).

The integration baseline is the latest accepted household/member-management product, not `main`. Main remains the assignment grading version. Verify the actual target commit before work; do not assume the remote contains local Phase 4 changes.

Preserve existing onboarding, SMTP verification, invitations, ownership/lifecycle, selected-household authorization, Ask Hestia, cleaned task routes, UI and feature tests. Integrate feature responsibilities; do not replace whole shared files with a branch's version. Every new household route must use the shared context and current mutation authorization.

Branch names must never contain `codex`. Do not add collaborators/reviewers/assignees or coauthor attribution. Keep configured Git identity. No push, main merge, deployment or grading database changes without explicit user instruction. Preserve unrelated local edits and private configuration; never commit `.env`, `user_input.md` or user databases.

For merge work, use the optional repository skill at `.agents/skills/hestia-integration/SKILL.md`. The guide supplies the acceptance gate and handoff checklist; do not weaken existing tests to obtain a clean merge.
