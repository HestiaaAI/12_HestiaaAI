---
name: hestia-integration
description: Use when merging or porting Hestia teammate branches, resolving shared-file conflicts, or adding household-scoped feature routes to the demo application.
---

# Hestia feature integration

Read the repository root AGENTS.md and docs/TEAM_MERGE_GUIDE.md before edits. Resolve paths from the repository root, not this skill folder.

1. Verify clean/safely preserved local state, exact accepted integration target and incoming commit/ancestry. Main is grading, not the demo baseline.
2. Create a feature integration branch from the accepted target and a local backup reference. Simulate conflicts before merging; never reset teammates' branches or discard their commits.
3. Integrate domain features using the existing selected-household context, fresh transactional permission checks, canonical navigation and model identities. Follow the guide's specific migration, privacy, receipt, payment and thermostat decisions.
4. Add meaningful regressions for integration failures, run existing and incoming feature suites, and apply migration/packaging/browser gates. Retain real authorization and feature assertions when adapting obsolete route fixtures.
5. Produce the guide's handoff record. Do not merge to the shared target while required gates fail, push/deploy without authorization, change grading data, or add collaborator/coauthor metadata.

Example: keep the canonical household roster and invite/lifecycle services; add thermostat preferences as its subfeature instead of restoring the incoming grocery-owned household page. Route expenses through the same active selection instead of a second expense household picker.
