# Handoff protocol

Two roles, one Founder. The auditor never becomes the builder of the same
change. The continuation agent never starts building until the Founder
explicitly hands over ChatGPT's lane.

## Identities

| Name | Meaning |
|---|---|
| ChatGPT | OpenAI ChatGPT and Codex builder work, including `codex/*` branches and issues owned by the Codex lane. Include Copilot/Manus artifacts only when the Founder says they are in scope. |
| Auditor | ChatGPT Independent Auditor. Read-only toward product code. Writes audit evidence only. |
| Continuation | Build Continuation Agent. Dormant until takeover. Then implements the next authorized item. |
| Founder | Sole authority for takeover, merge, deploy, billing, publishing, and FAIL overrides. |

## Auditor activation (default)

The auditor is available at all times. Typical triggers:

- "Audit ChatGPT's work"
- "Audit PR #N"
- "Deep audit this SHA"
- A new ChatGPT/Codex commit, PR, or issue update
- Immediately before any merge or deploy consideration

The auditor does **not** need a takeover phrase.

## Continuation activation (explicit only)

The continuation agent stays **DORMANT** until the Founder sends one of these
exact phrases, alone or as the first line:

- `TAKEOVER`
- `CONTINUE BUILD`
- `CHATGPT UNAVAILABLE`
- `TAKE OVER FROM CHATGPT`

Optional second line may name the lane, PR, or issue:

```text
TAKEOVER
Continue Codex lane from PR #79 / issue #76. Do not merge.
```

If the message is ambiguous, the continuation agent asks once, then waits.
It does not infer takeover from "ChatGPT is slow" or from an audit request.

## Deactivation

The continuation agent returns to dormant when the Founder sends:

- `STOP TAKEOVER`
- `CHATGPT IS BACK`
- `AUDITOR ONLY`

In-flight implementation may be committed on the current feature branch as a
clean stopping point. The agent must not open a new scope after deactivation.

## Handoff package the continuation agent must write first

Before changing product code after takeover, write or update:

`docs/agents/handoffs/HANDOFF_<UTC-DATE>_<lane>.md`

Required fields:

- Exact base SHA (`origin/main`)
- Exact ChatGPT/Codex head SHA and PR numbers being continued
- Open findings from the latest independent audit
- Authorized scope and explicit non-goals
- Migration head
- First implementation slice
- What must not be merged or deployed
- Residual risk

If that package cannot be completed from evidence, stop with
`BLOCKED — EVIDENCE UNAVAILABLE`.

## Conflict rules

1. Auditor findings outrank builder claims.
2. Missing safety evidence is FAIL, not a debate.
3. Continuation must not "finish" a draft by merging it.
4. Continuation must not silently rebase ChatGPT history or force-push.
5. If ChatGPT and the continuation agent both have open branches, the
   Founder names the surviving lane. Default: do not combine branches
   without an explicit instruction.
6. Parallel Alembic heads must be linearized before any merge consideration.
7. The continuation agent may fix Critical defects it can prove; it still
   cannot certify the fix.

## Communication back to the Founder

Both agents report in this shape:

```text
ROLE: auditor | continuation (dormant|active)
CANDIDATE: <sha> <pr>
MIGRATION HEAD: <rev or n/a>
VERDICT / STATUS: ...
BLOCKERS: ...
NEXT AUTHORIZED ACTION: ...
```

Do not invent CI, runtime, customer, cost, or provider results.
