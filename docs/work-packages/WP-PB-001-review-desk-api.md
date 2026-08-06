# Work Package WP-PB-001 — Private Beta Review Desk API

**Status:** Implemented — local verification green  
**Priority order fit:** Revenue → Customer value → Platform reliability  
**Launch impact:** Unlocks demoable Human Review Gate for Private Beta / first paying design partners

---

## Objective

Expose the existing orchestration Review Gate as a **customer-reachable product surface**: submit a content draft into a mandatory review queue, list awaiting gates, approve/reject with audit — without waiting for BYOK generation or Stripe.

## Business value

- The Gate is the commercial wedge (PMF audit). Today it is **engine-only** (0 HTTP/UI reachability).
- Agencies cannot evaluate or pay for a product they cannot operate.
- This is the shortest path to a Private Beta demo: **draft → Review Gate → decision**.

## Technical design

1. **Default workspace workflow** `agency_content_desk` v1:
   - `scripting` → `review` (gate) → `published` (terminal on approve)
   - Reject with no `on_review_rejected` edge → **fail the run** (loud, no silent success)
2. **`POST /workspaces/{id}/content-jobs`** (admin/editor):
   - Create `content_items` + `content_versions` (draft script)
   - Start pipeline; immediately complete `scripting` with provided draft (stub generation for beta)
   - Land in Review Gate (fail-closed; Gate non-bypassable)
3. **Review APIs** (list: any member; decide: admin/reviewer):
   - `GET /workspaces/{id}/review-gates`
   - `GET /workspaces/{id}/review-gates/{gate_id}`
   - `POST /workspaces/{id}/review-gates/{gate_id}/decision`
4. **Service-role writes** after membership/role guards (pipeline/gate/outbox lack tenant INSERT/UPDATE policies).
5. **Register outbox consumers + relay tick** in API lifespan (non-test); decision endpoint also dispatches pending review events in-request for snappy UX.
6. **Minimal web Review Desk** (token + workspace, queue, submit, approve/reject).
7. Fix Vite `/api` proxy rewrite so frontend hits FastAPI paths.

**Out of scope (next WPs):** Stripe, Slack/email notify, real BYOK provider executor, monthly spend cap, SSO.

## Risks

| Risk | Mitigation |
|------|------------|
| RLS blocks orchestration writes | Service-role session after explicit authz guards |
| Editors approving via API | Role guard: admin/reviewer only (matches `review_decisions` RLS) |
| Gate bypass | No path sets published without `submit_review_decision` |
| Stub generation mistaken for production AI | Document as Private Beta; `generated_by=private_beta_draft` |
| Relay not running → stuck after approve | Lifespan relay + in-request dispatch |

## Acceptance criteria

- [x] Authenticated admin/editor can create a content job that appears in awaiting review queue
- [x] Authenticated admin/reviewer can approve → run reaches `published` / succeeded
- [x] Authenticated admin/reviewer can reject → run fails with reason `review_rejected`
- [x] Non-member receives 403; editor cannot decide (403)
- [x] Cross-workspace gate access returns 404/403 (no leak)
- [x] Web Review Desk can list and decide using bearer token
- [x] Tests cover happy path + authz negatives
- [x] CHANGELOG / Roadmap / architecture updated (CI on PR)

## Test strategy

- API integration tests with real Postgres + JWT (existing conftest pattern)
- Cases: create→awaiting, approve→published, reject→failed, editor forbidden on decide, cross-workspace isolation
- Web: unit test for API client helper / build passes

## Rollback strategy

- Feature is additive (new routes + UI). Rollback = revert deploy / disable routers.
- No schema migration in this WP → no Alembic downgrade required.
- In-flight gates created in beta remain queryable; no data migration.

## Estimated implementation effort

**Medium — one focused iteration** (API + service + tests + minimal UI + docs). No new tables.
