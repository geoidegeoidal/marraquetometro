# Handoff

## README data-flow visual
- Objective: explain consultation versus optional regeneration without changing runtime behavior.
- Completed: branded accessible SVG embedded in README, with editable static HTML source in `docs/readme/`.
- Decisions: retain Outfit/Inter font stacks with system fallbacks; no remote diagram resources, invented map output or credentials.
- Verification: desktop and actual 390px rendering, safe SVG/source checks, eight security tests and redacted Gitleaks directory scan passed.
- Blocker: revocation of the historical ORS key remains unconfirmed; this documentation does not certify revocation.
- Next: review the documentation PR and its required `security` check; no merge is authorized by this change.
- Relevant baseline: `6edcc37093fb781e35465c27a9a13897d70b0493`.

## ORS credential containment
- Objective: remove embedded ORS credentials and reduce recurrence.
- Completed: eight generators use a shared environment reader; missing keys fail before side effects; raw ORS error logging removed; local env files ignored; offline regression tests and pinned Gitleaks hook/CI added.
- Decisions: no dotenv dependency, no real-key tests, no history rewrite, no suppression of historical findings through an allowlist.
- Verification: see the associated PR for exact commands/results; tests use mocked network and synthetic keys only.
- Blocker: the owner must revoke the exposed key in ORS. Source removal is not proof of revocation.
- Next: install pre-commit in every clone; enable GitHub push protection/required security checks where available.
- Baseline: `0c1385493a3ea52dcb2bd4dd149384d12a444589`.
