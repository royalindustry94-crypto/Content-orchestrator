# Release discipline — CEO reference

Content Orchestrator ships by **milestone workstream**, not by vibes.

## Workstream lifecycle (required order)

```text
DESIGN doc  →  IMPLEMENT  →  TESTS + MIGRATIONS  →  AUDIT  →  CI GREEN  →  VERIFIED
     ↑                                                                      |
     └──────── no production schema/behavior before design ────────────────┘
```

| Artifact | When |
|---|---|
| `docs/M{n}_WS{k}_DESIGN.md` | Before production code |
| Migrations + models + code | After design commit |
| `docs/M{n}_WS{k}_IMPLEMENTATION.md` | With or immediately after impl |
| `docs/M{n}_WS{k}_AUDIT.md` | After adversarial review + gates |
| CI green on PR HEAD | Before VERIFIED |

## Verification checklist

Copy into audit docs / CEO go-no-go:

- [ ] Design landed in its own commit (or clearly first)
- [ ] `alembic upgrade head` on clean DB
- [ ] Downgrade/upgrade roundtrip for new revisions
- [ ] `ruff check` clean (api + worker)
- [ ] `pytest -W error` full API suite
- [ ] Worker tests green
- [ ] Web lint/typecheck/build if UI touched
- [ ] Adversarial RLS tests for every new table/policy
- [ ] Concurrency / race tests for locks (claim, spend, leases)
- [ ] No placeholder / TODO greps in changed paths
- [ ] Audit lists defects found/fixed + remaining risks
- [ ] Final status: **VERIFIED** / **FAILED** / **NOT VERIFIED**
- [ ] PR updated; **not merged** unless human explicitly orders merge

## Completion report (cloud / CEO)

When closing a workstream, require:

1. Branch  
2. Commit SHA  
3. PR URL  
4. GitHub Actions URL  
5. Migration head  
6. Tests passed  
7. Coverage  
8. Security findings  
9. Defects found and fixed  
10. Remaining risks  
11. Final status  

## Merge policy

- Default: **do not merge**.
- Merge only on explicit human directive after VERIFIED.
- Never force-push shared milestone branches.
- Never rewrite history to hide failed gates.

## Regression policy

- Completed M3 and prior M4 workstreams are sacred.
- A WS that breaks prior suites is **FAILED** until fixed — not “mostly done.”

## Advisory automation

Run from repo root (optional):

```bash
bash .cursor/skills/ceo/scripts/ceo-release-gate.sh
```

The script is advisory. The CEO still issues APPROVE/REJECT.
