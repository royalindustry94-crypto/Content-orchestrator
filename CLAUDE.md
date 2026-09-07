# Claude Code instructions

Read and follow `AGENTS.md` before planning or changing anything in this repository.

- Preserve the Human Review Gate, FORCE RLS workspace isolation, spend controls, provider abstraction, and audit logging.
- Do not weaken security or CI gates.
- Do not commit secrets or `.env` files.
- Use a branch and pull request for changes; do not push directly to `main`.
- Run the relevant tests and report exact evidence before proposing a merge.
- Treat product-code changes as out of scope unless the user explicitly requests them.
