# Handoff

## ORS credential containment
- Objective: remove embedded ORS credentials and reduce recurrence.
- Completed: eight generators use a shared environment reader; missing keys fail before side effects; raw ORS error logging removed; local env files ignored; offline regression tests and pinned Gitleaks hook/CI added.
- Decisions: no dotenv dependency, no real-key tests, no history rewrite, no suppression of historical findings through an allowlist.
- Verification: see the associated PR for exact commands/results; tests use mocked network and synthetic keys only.
- Blocker: the owner must revoke the exposed key in ORS. Source removal is not proof of revocation.
- Next: install pre-commit in every clone; enable GitHub push protection/required security checks where available.
- Baseline: `0c1385493a3ea52dcb2bd4dd149384d12a444589`.
