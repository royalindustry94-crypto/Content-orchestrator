# Agent Reliability Foundation

This repository gives Cursor, Codex, and humans the same project rules and verification procedures. Agent confidence is not release evidence; exact commands and observed results are.

## Components

| Component | Location | Purpose |
|---|---|---|
| Always-on invariants | `AGENTS.md` | Product and safety boundaries |
| Directory guidance | `apps/*/AGENTS.md` | API, migration, web, and worker conventions |
| Shared procedures | `.agents/skills/` | Portable planning, audit, migration, browser, and release workflows |
| Coordination protocol | `.agents/coordination/` | Cross-agent handoff schema and authority boundaries |
| Published handoffs | `.agents/handoffs/` | Branch-scoped messages between different apps or machines |
| Cursor reviewers | `.cursor/agents/` | Three focused read-only independent contexts |
| Scoped Cursor rules | `.cursor/rules/` | Attach relevant guidance by file path |
| Safety hooks | `.cursor/hooks.json` | Block dangerous shell operations and credential reads |
| Local evidence runner | `scripts/agent-check.sh` | Run consistent checks and save evidence |
| Cloud environment | `.cursor/environment.json` | Reproducible Postgres/API/worker/web setup |

## Normal workflow

1. Use `milestone-plan` for work whose scope or acceptance evidence is not already explicit.
2. Implement on a feature branch. Do not combine unrelated product and agent-infrastructure changes.
3. Run `scripts/agent-check.sh quick` while developing.
4. Run `scripts/agent-check.sh full` on the candidate. The database guard permits replay only on localhost databases ending `_test`.
5. Invoke the appropriate read-only Cursor reviewer:
   - `/security-auditor` for trust-boundary changes.
   - `/migration-auditor` for schema changes.
   - `/release-verifier` for the final exact-head decision.
6. Open or update a PR only when authorized. Required hosted checks must run on the exact head.
7. Merge or deploy only with explicit authority and complete evidence.

For a task transfer, use the `agent-handoff` skill and `scripts/agent_handoff.py`. Local handoffs stay in ignored validation logs. Published handoffs are committed to the task branch so another repository-aware app can verify them. Cursor and Codex do not otherwise share a live conversation channel.

## Verification outcomes

The evidence runner writes under ignored `validation-logs/agent-check/`. `NOT-RUN` is intentionally distinct from `PASS`; Docker, Gitleaks, browser tooling, and hosted CI may not exist in every local environment. A full run exits with status 3 and `PARTIAL` if any local check group is unavailable.

Useful commands:

```bash
scripts/agent-check.sh identity
scripts/agent-check.sh quick
scripts/agent-check.sh full
```

The full command can update and replay the configured disposable test database. It refuses non-local hosts and database names that do not end in `_test`.

## Safety-hook boundaries

Cursor hooks reject tested high-risk forms of force pushes, direct pushes to `main`, hard resets, forced cleans, recursive or scripted deletion, direct Alembic downgrades, raw database-client use, and common credential-file reads. Migration replay remains available through the guarded evidence runner.

Hooks are pattern-based defense in depth, not an operating-system sandbox or proof that arbitrary shell code is safe. Encoded commands, aliases, interpreters, newly installed tools, and early read-only Cloud Agent exploration can bypass project hooks. GitHub branch protection, isolated credentials, least-privilege service accounts, disposable local databases, and explicit approval boundaries remain authoritative.
