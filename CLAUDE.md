# Claude Code instructions

Read and follow `AGENTS.md` and `.github/AGENT_OPERATING_PROTOCOL.md` before planning or changing anything in this repository. `AGENT_OPERATING_PROTOCOL.md` is this repository's canonical agent operating model, covering roles, handoffs, and Build Watchdog continuity rules; this file adds Claude-specific safeguards on top of it.

- Work only on an explicitly assigned issue and scope.
- Preserve the Human Review Gate, FORCE RLS workspace isolation, spend controls, provider abstraction, and audit logging.
- Do not weaken security or CI gates.
- Do not commit secrets or `.env` files.
- Use one task, one owner, one branch, and one pull request; never push directly to `main`.
- Run the relevant tests and report the exact head SHA and evidence before proposing a merge.
- If blocked or interrupted, leave a durable handoff with the blocker, last verified SHA, tests, and next action.
- Treat product-code changes as out of scope unless the Founder explicitly queues or requests them.
- Never auto-merge or bypass Founder approval, Human Review, CI, or an independent audit.
