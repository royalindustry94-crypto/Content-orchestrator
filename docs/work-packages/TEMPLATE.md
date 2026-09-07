# Work Package — <ID>: <title>

## Objective

One clear outcome. Keep the package small enough for one primary implementation worker to complete without a full-repository audit.

## Business value

Why this is the highest-value next change and what user/customer outcome it supports.

## Risk tier

`R0 | R1 | R2 | R3 | Release`

See `docs/AGENT_OPERATING_MODEL.md`.

## Acceptance criteria

- [ ] <observable outcome 1>
- [ ] <observable outcome 2>
- [ ] Existing non-negotiables in `AGENTS.md` remain intact
- [ ] Relevant tests pass

## In scope

- <surface/path/behavior>

## Out of scope

- <explicitly excluded work>

## Likely relevant files

- `<path>`

Do not treat this list as permission to scan the entire repository. Broaden context only when a concrete dependency requires it.

## Primary worker

Cursor by default.

## Targeted verification during implementation

- `<focused command/test/check>`

GitHub Actions performs the standard full-suite verification at PR.

## Escalation triggers for this package

Escalate only if one of these applies:

- a concrete blocker remains after focused debugging
- the task crosses an R3 boundary (auth/RLS, tenant isolation, Human Review Gate, spend controls, destructive migration, concurrency/data integrity)
- acceptance criteria require an architectural decision not covered by existing docs
- deterministic CI fails for a reason that cannot be resolved from the concrete failure

## Handoff evidence

```text
Objective completed:
Files changed:
Behavior changed:
Targeted tests run:
CI status:
Security/safety controls affected:
Unresolved risks:
Escalation required: YES/NO
Escalation reason (if YES):
Recommended next task:
```
