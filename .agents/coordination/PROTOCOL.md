# Cross-agent coordination protocol

Cursor, Codex, and other agents do not automatically share conversations or live memory. They coordinate through verifiable repository artifacts and, when configured, GitHub or Origin pull-request and issue events.

## Transport order

1. **Same workspace:** local JSON handoff in `validation-logs/agent-handoffs/`.
2. **Different app or machine:** published JSON handoff under `.agents/handoffs/<task-id>/` on the task branch.
3. **GitHub/Origin workflow:** PR body or comment links to the published handoff and exact head SHA.
4. **Future automation:** a scoped integration may translate issue/PR events into agent runs. It must preserve the same task ID, branch, SHA, and approval boundaries.

A published handoff is normally its own metadata-only commit after the implementation commit. Its `head_sha` identifies the exact implementation state being transferred; the handoff commit itself must not contain code changes. This avoids a circular claim in which a file tries to record the SHA of the commit that contains that file. The receiving agent uses `validate` while the task branch exists. CI uses `validate-all` for schema checks only because squash merges and branch deletion may legitimately remove historical commit objects; use `validate-all --require-commits` only in a clone that still has the task refs.

Never use an unrecorded chat statement as the only evidence that tests passed, a migration ran, or a deployment is safe.

Repository hooks reduce common mistakes but are not a security sandbox. Cross-app agents must still run with least-privilege credentials, protected branches, and no production access unless a separately approved task grants it.

## Ownership and isolation

- One writing agent owns a branch/worktree at a time.
- Parallel agents either work read-only or use separate branches/worktrees with disjoint scope.
- Reviewers are read-only and do not certify their own fixes.
- A handoff changes responsibility, not authorization.

## Escalation boundaries

Routine planning, implementation, local testing, auditing, and evidence collection may be automated. Explicit Founder or separately documented policy approval remains required for:

- merging protected branches;
- deploying or migrating staging/production;
- accessing real customer data or credentials;
- increasing or bypassing spend caps;
- enabling external publishing;
- destructive or difficult-to-recover operations.

These boundaries may only be changed through an explicit, version-controlled automation policy reviewed by the Founder.
