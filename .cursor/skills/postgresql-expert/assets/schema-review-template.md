# Schema / migration review record

**Date:** YYYY-MM-DD  
**Review ID:** PG-YYYYMMDD-##  
**Verdict:** APPROVE | CONDITIONAL | REJECT | ESCALATE  
**Reviewer:** PostgreSQL Expert

## Change summary

Revisions / tables / policies:

## Checklist

- [ ] Single migration head preserved
- [ ] upgrade + downgrade (or expand/contract plan)
- [ ] Fresh DB up → down → up proven
- [ ] `workspace_id` on tenant tables
- [ ] ENABLE + FORCE RLS; fail-closed policies
- [ ] Least-privilege grants
- [ ] Composite FKs/uniques prevent cross-workspace contamination
- [ ] Money as `numeric`; timestamps as `timestamptz`
- [ ] PK/FK/UNIQUE/CHECK/indexes adequate
- [ ] Immutable ledgers protected
- [ ] SECURITY DEFINER has locked `search_path` (if any)
- [ ] Query plans / indexes for hot paths considered
- [ ] Locking / SKIP LOCKED / races reviewed
- [ ] Idempotency unique constraints where needed
- [ ] Adversarial `app_runtime` RLS tests included
- [ ] No SQLite/mock as final validation

## Risks

-

## Conditions / rollback

-

## Escalation

Domain (if any): tenant isolation | data loss | financial | migration safety | concurrency  

Escalate to: `/ceo` / `/chief-architect`
