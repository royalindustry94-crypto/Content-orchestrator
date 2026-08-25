# Security audit checklist

Use on every audit. Mark each item Pass / Fail / N/A with evidence.

## Identity & session

- [ ] User JWT verified with project secret/audience; not minted by API
- [ ] Missing/invalid JWT → 401
- [ ] Workspace membership enforced (`require_workspace_member` / admin)
- [ ] Service-role sessions only after explicit authz guard
- [ ] RLS session sets `request.jwt.claim.sub` transaction-locally

## Tenant isolation

- [ ] Tenant tables have `workspace_id`
- [ ] ENABLE + FORCE RLS on tenant tables
- [ ] Policies fail closed (no `USING (true)` on tenant data)
- [ ] Adversarial outsider SELECT empty
- [ ] Forbidden INSERT/UPDATE/DELETE fail as runtime role
- [ ] No cross-workspace join/IDOR via client-supplied UUIDs

## Workers

- [ ] Per-worker credentials; secret hashed; constant-time compare
- [ ] Rotate / revoke / expiry enforced
- [ ] Uniform 401 on failure modes (no enumeration) where designed
- [ ] Revoked workers cannot claim/renew/submit
- [ ] Credentials not SELECT-able by `app_runtime` if designed service-only

## Injection & API abuse

- [ ] SQL via bound parameters / ORM only
- [ ] No shelling out on user input
- [ ] No path traversal on file/storage inputs
- [ ] SSRF: no open URL fetch from untrusted input without allowlist
- [ ] Mass assignment: Pydantic `extra` policy appropriate
- [ ] Pagination/payload limits where lists/uploads exist
- [ ] Rate limiting considered for auth and claim endpoints

## Secrets & errors

- [ ] No secrets in repo or workflow logs
- [ ] Audit/outbox payloads scrubbed
- [ ] Production debug off; stack traces not returned to clients
- [ ] CORS allowlist not `*` with credentials in prod configs

## Control planes

- [ ] Human Review Gate cannot be skipped by worker/recovery/admin shortcut
- [ ] Spend: reservation + cap lock; no double-commit under concurrency
- [ ] Idempotency keys / effect keys prevent duplicate side effects
- [ ] Lease/DLQ/outbox cannot be abused to drop or duplicate privileged work silently

## Database privileges

- [ ] SECURITY DEFINER has locked `search_path`
- [ ] No GRANT ALL TO PUBLIC on tenant tables
- [ ] Least-privilege `app_runtime` grants

## CI / supply chain

- [ ] Workflow `permissions:` least privilege
- [ ] Third-party actions pinned (SHA or reviewed tags)
- [ ] Secrets not echoed; dangerous triggers reviewed
- [ ] `pip-audit` / `npm audit` run or documented unavailable

## Process

- [ ] Findings ranked; Critical/High = 0 for approval
- [ ] Regression tests for each defect
- [ ] Re-audit from step 1 after fixes
- [ ] Report complete; no merge by auditor
