# Claude Code instructions

Read and follow `AGENTS.md` first — it is authoritative, including its "Operating authority" section: standing authority to commit, push, resolve findings, and merge without per-change Founder approval. `.github/AGENT_OPERATING_PROTOCOL.md` adds the coordination model (roles, handoffs, Build Watchdog continuity) on top of that. Use [coordination hub #90](https://github.com/royalindustry94-crypto/Content-orchestrator/issues/90) for the current `CLAIM`, `HEARTBEAT`, and `HANDOFF` record before editing, if multiple agents are active on this repo at once.

- Preserve the Human Review Gate, FORCE RLS workspace isolation, spend controls, provider abstraction, and audit logging — these are product safety guarantees, not process gates, and are not any agent's to weaken.
- Do not weaken security or CI gates.
- Do not commit secrets or `.env` files.
- Use one task, one Builder, one branch, and one pull request when more than one agent is working the repo concurrently.
- Run the relevant tests, reproduce any review finding before trusting or dismissing it, and report the exact head SHA and evidence before merging.
- If blocked or interrupted, leave a durable handoff with the blocker, last verified SHA, tests, and next action.
- Real money, destructive/irreversible actions, and repo/org access changes still get flagged to the Founder clearly before acting, even without a formal approval step.
