# CI workflows & secrets

## GitHub Actions review

- Prefer explicit `permissions:` (contents/read default; escalate only when required)
- Pin third-party actions to full commit SHA when practical; otherwise review tag movers
- Avoid `pull_request_target` with untrusted checkout + secrets
- Do not echo secrets; mask carefully; never write secrets to artifacts
- PR workflows from forks should not expose privileged cloud credentials

## Secret scanning

- Scan working tree for high-entropy tokens, private keys, `.env` commits
- Scan recent Git history when releasing (`git log -p` / `gitleaks` / `trufflehog` if available)
- Confirm `.gitignore` excludes `.env`, credential files

## Dependency checks

| Ecosystem | Command (if installed) |
|---|---|
| Python | `pip-audit` or `python -m pip_audit` in `apps/api` / `apps/worker` |
| Node | `npm audit --omit=dev` or project standard in `apps/web` |

If tooling is missing: record **NOT RUN — tool unavailable** and escalate Medium unless CEO accepts residual risk; do **not** silently treat as Pass.

## Never

- Disable security tests to green CI
- Commit “temporary” secrets with “rotate later”
