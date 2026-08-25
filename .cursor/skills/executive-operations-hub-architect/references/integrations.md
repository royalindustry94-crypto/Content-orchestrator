# Hub integrations

## Required clean-interface rule

Every external system is reached through an **adapter** with an explicit
contract (events or APIs). No module reaches into another system’s DB or
scrapes UI as SoT.

## Integration matrix (baseline)

| System | Typical use | Interface ideas | Guardrails |
|--------|-------------|-----------------|------------|
| GitHub | PRs, checks, issues, deployments | GitHub Apps / webhooks / GraphQL | Least privilege; verify signatures |
| Cursor Background Agents | Spawn/monitor agent runs | Cursor APIs / agent metadata as available | No secret leakage into prompts/logs |
| CI/CD | Actions status on SHA | Checks API / workflow_run webhooks | Exact SHA discipline with `/release-manager` |
| PostgreSQL | Hub metadata and/or read models | Dedicated hub schema or service DB | Not a rewrite of product SoT |
| Business systems (future) | CRM/billing/ops tools | Webhooks + outbound connectors | `/ceo` scope; `/security-auditor` on tokens |

## Security

- Short-lived tokens; rotate; environment-scoped secrets (`/devops-engineer`)
- Audit every privileged integration action
- Threat-model agent tools that can write to GitHub or prod (`/security-auditor`)

## Failure modes

- Duplicate webhooks → idempotent keys
- Agent crash → hub task returns to actionable state; no silent success
- CI red → hub must not claim RELEASE READY
