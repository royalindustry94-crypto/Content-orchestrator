# CI/CD — Content Orchestrator

## Canonical workflow

Primary CI: `.github/workflows/ci.yml`

| Job | Working dir | What it proves |
|-----|-------------|----------------|
| `api` | `apps/api` | Postgres 16 service, `alembic upgrade head`, `ruff check`, `pytest` |
| `worker` | `apps/worker` | `ruff check`, `pytest` |
| `web` | `apps/web` | `npm ci`, `npm run lint`, `npm run build` (`tsc -b` + Vite) |

Triggers: `push` to `main`, all `pull_request`s.

## Least-privilege defaults

For every workflow (and prefer per-job):

```yaml
permissions:
  contents: read
```

Only add write / `id-token` / `packages` when a concrete step needs them; document why in the PR.

## Required practices

1. **Pin actions** to full SHAs when tightening supply chain (coordinate `/security-auditor`); at minimum keep major versions intentional (`@v4`).
2. **Do not** print secrets; mask sensitive env in logs.
3. **Fail closed** — do not `continue-on-error` on lint/test/migrate for ship jobs.
4. **Caches** are allowed (npm/pip) if they cannot substitute for tests.
5. **Services** — API tests need real Postgres (as CI already does); do not replace with SQLite for ship proof.

## Extending CI

When adding jobs:

- Mirror product boundaries (`api` / `worker` / `web`)
- Keep migration step ahead of API tests that assume schema
- If adding deploy workflows: separate from PR CI; require environment protection rules when production is involved
- Escalate new deploy topology to `/chief-architect`

## Local vs Actions

Local green is useful; **ship claims require Actions green on the pushed SHA**. Cite the Actions URL in DevOps output.
