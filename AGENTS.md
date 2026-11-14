# Security conventions

- Keep credentials out of code, browser assets, data, logs, fixtures and documentation.
- ORS generators must use `ors_config.require_ors_api_key()` and validate before network or writes.
- Do not log raw ORS responses or exceptions; they may contain credentials.
- `.env.example` must remain empty. Scripts read the process environment; there is no dotenv loader.
- Run `python -m unittest discover -s tests -v` and Gitleaks with full redaction before publishing.
- Never use a real API key in tests or print historical secrets in diffs/reports.
- Revocation happens at the provider. Source removal does not revoke or erase historical secrets.
