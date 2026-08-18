# Release Manifest — Cumulative Mission Control Stack

**Manifest date:** 2026-08-18 GMT+8
**Repository:** `royalindustry94-crypto/Content-orchestrator`
**Audit target:** `c91d9d3a3530b944801c50ad8f2be77879101e49`
**Base `main`:** `48ed04ad0d66881591554c39831397191ee5c2a4`
**Migration head:** `0035`

> **Scope rule:** This manifest identifies the only cumulative technical target reconstructed from the specified open PR stack. Evidence from another SHA must not be represented as evidence for this target.

## Candidate identity

The target is the head of PR #43, `c91d9d3a3530b944801c50ad8f2be77879101e49`. Local Git ancestry checks established that every listed PR head is an ancestor of the next one and that each branch traces to the recorded `main` base. Public PR #43 independently identifies the same seven-PR stack and final SHA.[1]

| Order | PR | Head SHA | Declared branch relation | Direct parent / integration predecessor |
|---:|---:|---|---|---|
| 1 | [#36][2] | `a0f0ad9447ef6ddaff29778764fc34fc71b42901` | `cursor/operations-dashboard-v1-b52d` → `main` | `48ed04ad0d66881591554c39831397191ee5c2a4` |
| 2 | [#37][3] | `35a1302da5711e958c7990e80c7ef8c0501f2918` | `cursor/operations-dashboard-v2-b52d` → PR #36 | `a0f0ad9447ef6ddaff29778764fc34fc71b42901` |
| 3 | [#38][4] | `653dd59465e19623314c40413a8f0fdb2684248e` | `feature/operations-dashboard-v3` → PR #37 | `35a1302da5711e958c7990e80c7ef8c0501f2918` |
| 4 | [#39][5] | `6038b6afe4bec86beefcc0d865013e3608c49099` | `cursor/mission-control-v4-b52d` → PR #38 | `38021487886d92e5112a8a09023934d0b24a0c8c` |
| 5 | [#40][6] | `0ca2f19e72c5f960242f36b46c0415312c17a0b6` | `cursor/ops-preview-seed-b52d` → PR #39 | `8655c52c91bcbb68898cdcdd2f8fc7abfda808f1` |
| 6 | [#41][7] | `c9fff90397b6aa0a90427fd54feef9e67fd3b076` | `cursor/lumora-ui-v1-b52d` → PR #40 | `2a000bca7fa17f9984e1f8a312d3d35001fce1be` |
| 7 | [#43][1] | `c91d9d3a3530b944801c50ad8f2be77879101e49` | `cursor/p0-reliability-sprint-b52d` → PR #41 | `b1ccd29707d12723ac85582371f7341652a743aa` |

The intervening parents for PRs #39–#43 are commits on the same verified linear ancestry and contain integration or follow-up changes between PR-head commits. PR #42 is excluded from this candidate, consistent with the candidate merge plan.[8]

## Migration graph

```text
0030
 ├─ 0031
 ├─ 0031_fk
 └─ 0031_spend_precision
       \
        0032_merge_p1
             ↓
            0033
             ↓
            0034_operations_leads
             ↓
            0035_worker_logs_v4
```

| Check | Result | Evidence state |
|---|---|---|
| Source graph has one final revision | `0035` | VERIFIED — source inspected and `alembic current` returned `0035 (head)` after fresh migration and replay. |
| Fresh install | Passed | VERIFIED — local PostgreSQL 16 `alembic upgrade head`. |
| Downgrade to base | Passed | VERIFIED — local PostgreSQL 16 `alembic downgrade base`. |
| Replay to head | Passed | VERIFIED — local PostgreSQL 16 re-upgrade to `0035`. |
| Schema metadata check | Passed twice | VERIFIED — `alembic check` reported no new upgrade operations after fresh upgrade and replay. |

## CI boundary

GitHub’s public commit checks page lists the five required CI checks—`api`, `worker`, `web`, `security`, and `docker-build`—for the target SHA. The public page directly exposed `web` as succeeded but required sign-in for full logs and did not expose a complete per-job conclusion or immutable workflow-run URL.[9] Therefore, **the GitHub CI suite on the exact SHA is PARTIALLY VERIFIED, not VERIFIED**. The independent local validation record is indexed in `docs/RELEASE_EVIDENCE_INDEX.md`.

## Merge authority

No merge is authorized by this manifest. The required protected merge sequence remains #36 → #37 → #38 → #39 → #40 → #41 → #43, with a new five-job CI pass after each retarget and protected merge.[8]

## References

[1]: https://github.com/royalindustry94-crypto/Content-orchestrator/pull/43
[2]: https://github.com/royalindustry94-crypto/Content-orchestrator/pull/36
[3]: https://github.com/royalindustry94-crypto/Content-orchestrator/pull/37
[4]: https://github.com/royalindustry94-crypto/Content-orchestrator/pull/38
[5]: https://github.com/royalindustry94-crypto/Content-orchestrator/pull/39
[6]: https://github.com/royalindustry94-crypto/Content-orchestrator/pull/40
[7]: https://github.com/royalindustry94-crypto/Content-orchestrator/pull/41
[8]: ./FULL_STACK_MERGE_PLAN.md
[9]: https://github.com/royalindustry94-crypto/Content-orchestrator/commit/c91d9d3a3530b944801c50ad8f2be77879101e49/checks
