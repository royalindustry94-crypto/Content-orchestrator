# Hub module map (starter)

| Module | In | Out | Notes |
|--------|----|-----|-------|
| Work intake | Goals, issues | Hub tasks | Deduplicate |
| Agent broker | Tasks | Agent runs | Cursor BG agents |
| Approval desk | Evidence packs | Ops approve/reject | ≠ product Review Gate |
| Release board | CI/QA/Security/Release reports | Readiness signal | Feeds `/release-manager` |
| Integration bus | Webhooks | Normalized events | Idempotent |
| Audit & notify | Domain events | Audit log + alerts | No secrets |
| Hub console | Operators | UI actions | Prefer separate from tenant app |
