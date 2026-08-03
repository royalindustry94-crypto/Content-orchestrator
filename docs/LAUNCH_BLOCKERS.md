# Launch Blockers

**Repository:** Content Orchestrator  
**Updated:** 2026-08-03 — P-002 closed on `cursor/p2-beta-launch-b52d`  
**Source of truth:** Fresh DR drill + integrated regression (not prior chat claims)

**Rule:** Nothing ships to private beta while any **P0** item remains open.
P0 is frozen. P1 Private Beta blockers are closed.

---

## Verdict

| Target | Status |
|--------|--------|
| Private beta | **READY FOR PRIVATE BETA** |
| Production | **BLOCKED** (managed PITR / paid Stripe go-live / optional APM — post-beta) |

---

## P0 — CLOSED (frozen)

All P0 checklist items remain CLOSED. Do not modify unless Critical defect.

---

## P1 — status

| ID | Item | Status | Evidence |
|----|------|--------|----------|
| P-001 | Stripe / billing | **CLOSED** | `0031` + entitlement gate; default off |
| P-002 | Hosted/staging backup restore drill | **CLOSED** | `docs/DISASTER_RECOVERY_REPORT.md` |
| P-003 | CI CVE fail-closed | **CLOSED** | `pip-audit` / `npm audit` fail job |
| P-004 | Dependency CVE remediation | **CLOSED** | PyJWT + FastAPI/Starlette/Vite floors |
| P-005 | OpenAPI lockdown | **CLOSED** | Docs only in development |
| P-006 | Unindexed FK columns | **CLOSED** | `0031_fk`; probe = 0 |
| P-007 | AGENTS.md / Cursor rules | **CLOSED** | Root `AGENTS.md` + `.cursor/rules` |
| P-008 | Observability / on-call | **CLOSED** | `/metrics` + `ON_CALL.md` |
| P-009 | Spend Numeric precision | **CLOSED** | Caps `numeric(12,4)` |

**Alembic:** single head `0032_merge_p1` (merge of `0031`, `0031_fk`, `0031_spend_precision`).

---

## Related

- `docs/FINAL_RELEASE_AUDIT.md`
- `docs/DISASTER_RECOVERY_REPORT.md`
- `docs/BETA_RELEASE_CHECKLIST.md`
- `docs/EXECUTIVE_STATUS_REPORT.md`
