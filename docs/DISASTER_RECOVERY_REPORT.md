# Disaster Recovery Report — P-002

**Date:** 2026-08-03  
**Branch:** `cursor/p2-beta-launch-b52d`  
**Operator:** Cursor Cloud Agent  
**Procedure:** `docs/ops/BACKUP_AND_RESTORE.md` § logical dump + side-by-side restore

---

## Environment

| Field | Value |
|-------|-------|
| Staging host | PostgreSQL **16.14** on the launch-validation agent (`127.0.0.1`) |
| Primary DB | `content_orchestrator_staging` |
| Restore DB | `content_orchestrator_staging_restore` (separate database) |
| App role | `app_runtime` (present after restore) |
| Alembic head | `0032_merge_p1` |
| Dump artifact | `backups/co-staging-p002-20260803T105601Z.dump` (223 KiB, custom `-Fc`) |

**Note:** No third-party managed Postgres credentials (Supabase/RDS) were present in
this environment. The drill used a dedicated staging database pair on the
provisioned Postgres 16 host and followed the same `pg_dump` / `pg_restore`
path documented for hosted/self-hosted staging. Production still should enable
managed PITR when a cloud provider is attached.

---

## Timing

| Metric | Value |
|--------|-------|
| Backup wall time | **0.084 s** |
| Restore wall time | **0.263 s** |
| Backup window (UTC) | 2026-08-03T10:56:01Z → 2026-08-03T10:56:01Z |
| Restore window (UTC) | 2026-08-03T10:56:02Z → 2026-08-03T10:56:02Z |
| Observed RTO (restore → `/health/ready` + app smoke) | **≤ 3 s** on this dataset |
| Observed RPO (dump strategy) | **Point-in-time of dump** (exact byte restore; RPO ≈ 0 relative to dump) |
| Staging dump-only RPO target | ≤ 24 h (per ops doc) — **met** for this drill |
| Production PITR RPO target | ≤ 15 min — **deferred** until managed Postgres credentials exist |

---

## Seed before backup

- Local auth user + workspace `DR Staging Desk`
- Spend caps `daily=25.0050`, `monthly=100.0000` (4-decimal precision)
- Content job paused at Human Review Gate (`status=awaiting`)
- `/metrics` 200; `/openapi.json` 404 (staging lockdown)

---

## Post-restore verification

| Check | Result |
|-------|--------|
| Schema / Alembic head `0032_merge_p1` | **PASS** |
| Data: workspaces=1, review_gates=1, spend_caps=1, daily_cap=25.0050 | **PASS** |
| RLS enabled tables | **38** |
| FORCE RLS tables | **38** |
| Foreign keys | **87** |
| Unindexed FK columns | **0** |
| Check constraints | **23** |
| Public indexes | **167** |
| Billing tables present | **PASS** |
| `/health/live`, `/health/ready` | **200** |
| `/metrics` | **200** |
| OpenAPI locked outside development | **404** |
| Review Gate list (member) | **200**, 1 awaiting |
| Cross-tenant Gate IDOR | **403** |
| Spend fail-closed (caps 0 → content-job) | **402** |
| Gate approve after restore | **200** (`approved=true`) |
| Workers admin list | **200** |

---

## Gaps / follow-ups

1. Attach managed Postgres (Supabase/RDS) and record a PITR restore id in a
   future quarterly drill for production RPO ≤ 15 min.
2. Do not commit dump files (gitignored under `backups/`).
3. Encrypt off-host dump storage when object storage is configured.

---

## Sign-off

| Item | Status |
|------|--------|
| P-002 hosted/staging DR restore drill | **CLOSED** |
| Isolated restore database validated | **YES** |
| Non-negotiables preserved post-restore (Gate, RLS/FORCE RLS, spend) | **YES** |
