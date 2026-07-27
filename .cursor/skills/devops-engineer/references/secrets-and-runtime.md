# Secrets & runtime configuration

## Rules

1. **No secrets in git** — not in workflow YAML, Dockerfiles, compose overrides committed with prod creds, or client bundles.
2. **Environment-driven** — `DATABASE_URL`, JWT secrets, provider keys via env / secret manager / Actions secrets.
3. **Least exposure** — inject at runtime; do not bake into images.
4. **CI secrets** — use GitHub Actions secrets; scope to environments when available.
5. **Logs** — never log Authorization headers, JWT contents, or connection strings with passwords.

## Local compose

`docker-compose.yml` may use **dev-only** passwords for local Postgres. Production must not reuse those values. Document the split in deploy docs when adding prod compose/IaC.

## Checklist before deploy approval

- [ ] No new hardcoded secret in diff
- [ ] Required env vars listed for api / worker / web
- [ ] Actions secrets named and present for target env (or NOT VERIFIED)
- [ ] Rotation owner identified if secrets added
- [ ] Supply-chain / permission changes reviewed (escalate `/security-auditor` if token write or OIDC added)

## Observability baseline

Ship or require:

- Structured application logs (no secrets)
- Deploy/version identifier in logs or headers when available
- Alert path for failed migrate / crash-looping workers / failing readiness

If metrics/alerts tooling is not in-repo yet, document the gap under **NOT VERIFIED** or residual risks — do not pretend coverage exists.
