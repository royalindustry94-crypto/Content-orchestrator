# Published agent handoffs

Cross-environment handoffs may be stored here with:

```bash
scripts/agent_handoff.py create ... --publish
```

Each task uses its own directory and each message uses a microsecond timestamped JSON file to avoid parallel-write conflicts. A ready or verified handoff requires a clean worktree and records both commit and tree identity. Validate a received file while its task branch still exists:

```bash
scripts/agent_handoff.py validate .agents/handoffs/<task-id>/<file>.json
```

Do not place secrets, customer data, tokens, or raw provider payloads in handoffs.
