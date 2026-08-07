# Lumora UI Audit

**Audit date:** 2026-08-07  
**App under test:** `apps/web` on branch tip `cursor/lumora-ui-v1-b52d` (Lumora shell + Mission Control V4 APIs)  
**Runtime:** Vite `http://127.0.0.1:5173`, API `http://127.0.0.1:8000`  
**Demo workspace:** Lumora HQ (`founder@lumora.local`)  
**Method:** Live navigation of every primary screen + Mission Control tabs + mobile (390px) + drawer/menus; headless Chrome screenshots under `/tmp/cursor/artifacts/ui-audit/`  
**Scope:** Visual/UX audit only — **no redesign or UI fixes in this deliverable**

**UI score: 47 / 100**

---

## Screens audited

| # | Screen / surface | Desktop | Mobile | Screenshot(s) | Result |
|---|------------------|---------|--------|---------------|--------|
| 1 | Login / auth shell | Yes | — | `00-login.png` | Rendered |
| 2 | Dashboard (Operations Overview) | Yes | Yes | `00-dashboard.png`, `01-dashboard.png`, `16-mobile-dashboard.png`, `mobile-dashboard.png` | Rendered |
| 3 | Mission Control → Overview | Yes | Partial | `03-mission-overview-CRASH.png`, `03-mission-CRASH.png`, `12-mission-01-overview.png` | **Blank crash** |
| 4 | Mission Control → Timeline | Attempted | — | `12-mission-02-timeline.png` | **Blocked by crash** |
| 5 | Mission Control → Live Logs | Attempted | — | `12-mission-03-live-logs.png` | **Blocked by crash** |
| 6 | Mission Control → AI Assistant | Attempted | — | `12-mission-04-ai-assistant.png` | **Blocked by crash** |
| 7 | Mission Control → Content | Attempted | — | `12-mission-05-content.png` | **Blocked by crash** |
| 8 | Review Queue | Yes | Yes | `02-review-queue.png`, `04-review-queue.png`, `18-mobile-review.png` | Rendered |
| 9 | Review detail drawer | Yes | — | `13-review-drawer.png` | Partial / cascade failures |
| 10 | Pipelines | Yes | — | `03-pipelines.png`, `05-pipelines.png` | **Blank crash** |
| 11 | Workers | Yes | Attempted | `06-workers.png`, `19-mobile-workers.png` | **Blank crash** (nav cascade) |
| 12 | Customers | Yes | — | `07-customers.png` | **Blank crash** (nav cascade) |
| 13 | Leads | Yes | Attempted | `08-leads.png`, `20-mobile-leads.png` | **Blank crash** (nav cascade) |
| 14 | Analytics | Yes | — | `09-analytics.png` | **Blank crash** (nav cascade) |
| 15 | Billing | Yes | Attempted | `10-billing.png`, `mobile-billing.png` | **Blank crash** (nav cascade) |
| 16 | Settings | Yes | Attempted | `11-settings.png`, `mobile-settings.png` | Rendered when reached cleanly |
| 17 | Notifications popover | Attempted | — | `14-notifications.png` | Partial / cascade |
| 18 | Profile menu | Attempted | — | `15-profile.png`, `15-profile-menu.png` | Partial / cascade |
| 19 | Mobile nav drawer | — | Yes | `17-mobile-nav-open.png`, `mobile-nav-open.png` | Rendered from Dashboard |

**Primary entry:** `App.tsx` → `LumoraDashboard.tsx`  
**Legacy / unused shells still in tree:** `OperationsDashboard.tsx`, older desk styles in `app.css` (`:root` + `.desk` IBM Plex block precedes Lumora tokens)

---

## Executive findings

1. **Navigation is unsafe.** Changing `nav` does not clear `data` or force `loading` before paint. Views cast stale payloads (`as PipelineMonitor`, `as ExecutiveMode`, etc.) and crash with `TypeError`.
2. **No React error boundary.** One view crash unmounts the entire authenticated shell → blank dark screen; recovery requires full reload.
3. **Trust-breaking status copy.** Sidebar footer says “All systems operational” while Worker Health is Red (0/8 live) and critical alerts are visible.
4. **Purple-on-dark “AI default” look** (Inter/Manrope + `#9b87f5`) conflicts with earlier mint IBM Plex desk tokens still present in the same stylesheet.
5. **Mission Control secondary tabs could not be reliably audited** after Overview crash; treat Timeline / Logs / Assistant / Content as unverified in live session.

---

## Issues by priority

### P0 — Ship blockers (fix before any redesign)

| ID | Issue | Evidence | Where |
|----|-------|----------|-------|
| P0-1 | **Stale-data navigation crash** — `navigate()` only calls `setNav`; `data` remains previous screen’s shape while `loading` is still `false`. Next view renders with wrong payload → `TypeError`. | Console: `Cannot read properties of undefined (reading 'map')` in `PipelinesView`; Mission Overview crashes on `health.some` / shape mismatch; blank screens | `LumoraDashboard.tsx` `navigate` + `renderView` |
| P0-2 | **No error boundary** — crash blanks entire Mission Control shell with no recovery UI | `03-mission-CRASH.png`, empty `textLen: 0` captures | App root / shell |
| P0-3 | **Mission Control Overview unusable via normal nav** from Dashboard | Crash screens | Mission → Overview + `ExecutiveModeView` |
| P0-4 | **Pipelines / Workers (and often downstream nav) unusable** after cascade | `findings.json` pipelines exceptions; blank workers/customers/leads/analytics/billing | `PipelinesView`, workers pack, subsequent nav |
| P0-5 | **False “All systems operational”** while Worker Health is Red and critical alerts exist | Dashboard + Settings screenshots | Sidebar status footer vs `SystemHealthView` |

### P1 — Serious UX / product gaps

| ID | Issue | Evidence | Where |
|----|-------|----------|-------|
| P1-1 | Login always shows **Workspace name** on primary sign-in (signup-only concern) | Login a11y text dump | `App.tsx` auth form |
| P1-2 | Dashboard Quick Actions expose **unlabeled inputs** (“Workspace name”, “Pipeline topic”) | `findings.json` `unlabeled` | Dashboard / `QuickActionsView` |
| P1-3 | **Alerts metric (3) ≠ Recent Activity list (6)** — unclear aggregation | Dashboard screenshot | Dashboard metrics vs activity |
| P1-4 | **Critical vs Warning pills** visually similar (orange/gold) — severity hard to scan | Dashboard | Status chips |
| P1-5 | **Mobile search / ⌘K affordance weak or hidden**; top bar crowded | Mobile dashboard | Top bar responsive rules |
| P1-6 | **7 metric cards** dense on mobile (2-col grid) | `16-mobile-dashboard.png` | Dashboard metrics |
| P1-7 | Review Queue **metadata contrast low** (Pipeline / Workspace / Stage labels) | Review Queue screenshot | Review cards |
| P1-8 | **Duplicate CSS design systems** in one file (IBM Plex mint desk + Inter/Manrope purple Lumora) | `app.css` dual `:root` | Global styles |
| P1-9 | **Duplicate dashboard implementations** (`OperationsDashboard.tsx` vs `LumoraDashboard.tsx`) increase drift risk | Source tree | `apps/web/src` |
| P1-10 | Loading exists (skeletons) but **nav transition skips loading gate** (see P0-1) | Code path | `renderView` order |
| P1-11 | Empty states inconsistent / hard to verify after crashes; Review empty path not stress-tested with zero gates | Audit session | Multiple views |
| P1-12 | Notifications / profile / review drawer captures failed after cascade — **interaction surfaces under-verified** | Blank captures | Top bar overlays |

### P2 — Consistency, polish, accessibility

| ID | Issue | Evidence | Where |
|----|-------|----------|-------|
| P2-1 | Brand accent is **default AI purple** (`#9b87f5`) — conflicts with product differentiation goals | CSS tokens + screenshots | Design tokens |
| P2-2 | Typography stack **Inter + Manrope + DM Mono** — Inter is a default/AI-cluster font | `index.html` / CSS | Type system |
| P2-3 | Package / repo naming still “Content Orchestrator” while UI says Lumora | `package.json` / docs | Branding surface |
| P2-4 | Settings is **ops health + deploy metadata**, not account/workspace/billing prefs | Settings screenshot | Settings IA |
| P2-5 | Breadcrumbs are static “Lumora / {Page}” — not real hierarchy | All interior pages | Page header |
| P2-6 | Icon set is **inline custom SVG** only — no shared icon language / sizes documented | `LumoraDashboard.tsx` `PATHS` | Icons |
| P2-7 | Motion limited (status pulse, sidebar); **no intentional page transitions** after load | Visual review | Motion |
| P2-8 | Focus rings / keyboard path for sidebar, drawers, Approve/Reject not verified to WCAG | Not instrumented | A11y |
| P2-9 | Live “Updated just now” is decorative — not tied to real freshness of failing subsystems | Sidebar footer | Status UX |
| P2-10 | Command palette / global search mapping incomplete vs nav labels | `CommandPalette` mapping | Search |
| P2-11 | Review cards use **card-heavy** layout; Approve/Reject on every card may cause misclicks without confirm | Review Queue | Interaction design |
| P2-12 | Mobile hamburger works from Dashboard; **post-crash mobile routes blank** | Mobile workers/leads/billing blank | Mobile nav |

### P3 — Nice-to-have / backlog

| ID | Issue | Evidence | Where |
|----|-------|----------|-------|
| P3-1 | Greeting “Good morning.” with no personalization beyond time | Dashboard | Copy |
| P3-2 | Pipeline IDs truncated hex — hard for humans without copy affordance | Review cards | Content |
| P3-3 | Deployment branch shown in Settings may confuse non-engineers | Settings | Audience fit |
| P3-4 | Auth marketing column competes with form on narrow widths (not fully mobile-audited) | Login desktop | Auth responsive |
| P3-5 | Skeleton count fixed at 6 — may not match destination layout | `Loading` component | Loading polish |
| P3-6 | No documented empty illustrations / illustration system | Code | Empty states |
| P3-7 | Dead legacy `.desk` review queue styles still in CSS | `app.css` | Cleanup |

---

## Category checklist

| Category | Verdict |
|----------|---------|
| Outdated layouts | Mixed — Lumora shell is new; Mission Control panels retain denser ops-desk patterns; legacy CSS still present |
| Inconsistent styling | **Fail** — dual token systems, purple vs mint, panel chrome differs across imported V4 views |
| Poor UX | **Fail** — crashes, false health, alert count mismatch |
| Missing navigation | Partial — sidebar complete on paper; Mission tabs unreachable after crash |
| Missing loading states | Partial — skeletons exist but skipped on nav (P0) |
| Missing empty states | Partial / unverified under crash conditions |
| Mobile issues | **Fail** — density, search, crash cascade |
| Accessibility | **Fail** — unlabeled inputs, contrast risks, no error recovery, crash = total loss |
| Branding inconsistencies | **Fail** — Lumora UI vs Content Orchestrator repo/package; purple default look |
| Duplicate components | **Fail** — `OperationsDashboard` + `LumoraDashboard`; dual CSS; panels split across 3 files |

---

## Biggest UX problems (ranked)

1. **White/blank screen on navigation** (stale data + no error boundary)  
2. **Mission Control / Pipelines / Workers effectively broken** in normal click-paths  
3. **Sidebar health lie** (“All systems operational” vs Red workers)  
4. **Login workspace field** confusing for returning users  
5. **Mobile density + weak search** for an ops tool meant to be used under pressure  
6. **Alert count vs activity list mismatch** erodes trust in metrics  

---

## Estimated work required (technical scope — not calendar)

| Workstream | Scope |
|------------|-------|
| **P0 stability** | Clear/`null` data + set loading synchronously on nav/tab change; type-narrow before render; add app-level `ErrorBoundary` with retry; regression tests for every `NavKey` × Mission tab transition |
| **P0 trust** | Drive sidebar status from real health aggregate (worst status wins); never hardcode “operational” |
| **P1 UX/a11y** | Split login vs signup fields; label Quick Action inputs; reconcile alert metrics; severity color tokens; mobile top-bar / metric grid pass |
| **Design system consolidation** | Single `:root` token set; retire unused `OperationsDashboard` or quarantine; unify panel chrome from V4 imports |
| **Screen completion audit** | Re-capture Mission tabs, overlays, empty states after P0; fill true empty/error patterns per screen |
| **Implementation plan follow-through** | See `docs/UI_IMPLEMENTATION_PLAN.md` — design tokens, components, responsive, motion — **implementation deferred until CEO approves** |

**Rough size:** medium–large frontend reliability + design-system unification across ~10 nav screens + 5 Mission tabs + auth; **no API contract changes required** for P0 crash fix; health-footer truth may need only existing health payload.

---

## Artifact index

Screenshots and machine findings: `/tmp/cursor/artifacts/ui-audit/` (`findings.json` + PNGs listed above).
