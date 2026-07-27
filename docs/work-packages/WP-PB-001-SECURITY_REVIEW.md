# Security Review — WP-PB-001 Review Desk API

**Reviewer role:** Implementing engineer (self-review before merge)  
**Date:** 2026-07-27

## Threat model (delta)

| Threat | Control |
|--------|---------|
| Cross-tenant gate/content read | Membership guard + workspace_id scoped queries; negative test included |
| Editor approves publish | `require_workspace_reviewer` (admin/reviewer only); matches `review_decisions` RLS insert roles |
| Non-member creates jobs | `require_workspace_content_author`; 403 otherwise |
| Gate bypass / auto-publish | No route sets `published` without `submit_review_decision` + consumer resume |
| Privilege escalation via service role | Service-role used **only after** explicit FastAPI authz; no anonymous path |
| Token leakage in UI | Token kept in `sessionStorage` (tab-scoped); not logged; Private Beta only |
| Audit PII/secrets | Audit events log ids only; notes not written to audit logger |

## Residual risks

- Private Beta UI trusts operator-supplied JWT (no Supabase embedded auth yet) — acceptable for design partners; WP needed for real login.
- Service-role writes bypass RLS by design — must never call without prior guard (pattern matches concurrency/worker admin routes).

## Verdict

**Accept for Private Beta** with follow-up WP for Supabase-auth web login and Stripe entitlement checks.
