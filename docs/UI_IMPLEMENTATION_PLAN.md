# Lumora UI Implementation Plan

**Status:** Planning only — **do not implement until CEO approves after audit review**  
**Source audit:** `docs/UI_AUDIT.md` (2026-08-07)  
**Current shell:** `apps/web/src/LumoraDashboard.tsx` + `MissionControlV4.tsx` + `MissionControlPanels.tsx`  
**Constraint:** Reuse existing APIs; preserve Human Review Gate terminology; no placeholders or silent failures

This plan specifies **exact screens, components, and design-system rules** for the next UI pass. It does not redesign in code.

---

## 0. Delivery sequence (must follow)

1. **P0 stability** — nav data gating + error boundary + truthful health footer  
2. **Re-audit Mission tabs / overlays** with fresh screenshots  
3. **Design-system consolidation** (tokens, type, spacing, icons)  
4. **Screen-by-screen implementation** per §1 (no parallel redesign of every page)  
5. **Responsive + motion polish**  
6. **A11y pass + visual regression screenshots**

---

## 1. Exact screens

Each screen lists: purpose, primary components, data source, required states.

### 1.1 Auth — Login

| Field | Spec |
|-------|------|
| Route / state | Unauthenticated `App.tsx` |
| Purpose | Sign in to existing account |
| Layout | Split: brand panel (desktop) + form panel |
| Components | `AuthShell`, `AuthBrand`, `AuthForm`, `TextField`, `PasswordField`, `PrimaryButton`, `InlineError` |
| Fields | Email, Password only |
| States | idle, submitting, error (API message, never silent) |
| Notes | Workspace name **removed** from login; link to Create account |

### 1.2 Auth — Signup

| Field | Spec |
|-------|------|
| Purpose | Create account + first workspace |
| Components | Same as login + `WorkspaceNameField` |
| Fields | Email, Password, Workspace name |
| States | idle, submitting, error |

### 1.3 Shell (authenticated chrome)

| Field | Spec |
|-------|------|
| Purpose | Persistent navigation + workspace context |
| Components | `AppShell`, `Sidebar`, `SideNavGroup`, `SideNavItem`, `HealthFooter`, `TopBar`, `WorkspaceSwitcher`, `GlobalSearchTrigger`, `NotificationBell`, `ProfileMenu`, `MobileNavDrawer`, `ErrorBoundary`, `PageHeader`, `Breadcrumb` |
| Nav items (exact) | Dashboard · Mission Control · Review Queue · Pipelines · Workers · Customers · Leads · Analytics · Billing · Settings |
| Badge | Review Queue count from `listReviewGates` |
| Health footer | Derived from `getSystemHealth` worst status — never hardcoded “operational” |

### 1.4 Dashboard — Operations Overview

| Field | Spec |
|-------|------|
| Nav key | `dashboard` |
| Data | Parallel: executive, pipelines, alerts, activity, health, customers |
| Components | `PageHeader`, `MetricGrid`, `MetricCard`, `ActivityList`, `SystemHealthList`, `QuickActionsPanel`, `LiveBadge` |
| Metric cards (exact, ≤7) | Jobs Running · Jobs Completed Today · Reviews Waiting · Workers Online · Spend Today · Revenue · Alerts |
| States | loading (skeleton matching layout), empty activity, error+retry |
| Rules | Metric “Alerts” count must match documented aggregation rule (critical-only **or** all — pick one and label) |

### 1.5 Mission Control — Overview

| Field | Spec |
|-------|------|
| Nav + tab | `mission` / `overview` |
| Data | `getExecutiveMode` |
| Components | `MissionTabBar`, `ExecutiveModeView` (typed), `KpiStrip`, `OpsSummary` |
| States | loading, empty, error |
| Gate | Render **only** when `data` matches `ExecutiveMode` |

### 1.6 Mission Control — Timeline

| Field | Spec |
|-------|------|
| Tab | `timeline` |
| Data | `getUniversalTimeline` |
| Components | `UniversalTimelineView`, filters if already API-backed |
| States | loading, empty timeline, error |

### 1.7 Mission Control — Live Logs

| Field | Spec |
|-------|------|
| Tab | `logs` |
| Data | `getLiveLogs` + poll/refresh already in V4 |
| Components | `LiveLogsView`, log row, severity chip |
| States | loading, empty, streaming/error |

### 1.8 Mission Control — AI Assistant

| Field | Spec |
|-------|------|
| Tab | `assistant` |
| Data | Assistant panel existing endpoints |
| Components | `AssistantPanel`, message list, composer |
| States | idle, sending, error (visible) |

### 1.9 Mission Control — Content

| Field | Spec |
|-------|------|
| Tab | `content` |
| Data | `getContentCommand` |
| Components | `ContentCommandView` |
| States | loading, empty, error |

### 1.10 Review Queue

| Field | Spec |
|-------|------|
| Nav | `review` |
| Data | `listReviewGates` |
| Components | `ReviewSummaryBanner`, `ReviewCardGrid`, `ReviewCard`, `ReviewDrawer`, `ApproveButton`, `RejectButton` |
| Copy | Always “Human Review Gate” |
| States | loading, empty (“No reviews awaiting”), error, deciding (per-card busy) |
| A11y | Confirm destructive reject; focus trap in drawer |

### 1.11 Pipelines

| Field | Spec |
|-------|------|
| Nav | `pipelines` |
| Data | `getPipelineMonitor` |
| Components | `PipelineTable` or list, status chip, run meta |
| States | loading, empty, error |
| Gate | `PipelineMonitor` type guard before `.map` |

### 1.12 Workers

| Field | Spec |
|-------|------|
| Nav | `workers` |
| Data | monitor + timeline |
| Components | `WorkersView`, `WorkerTimelineView` |
| States | loading, empty (no workers), error |

### 1.13 Customers

| Field | Spec |
|-------|------|
| Nav | `customers` |
| Data | `getCustomers` |
| Components | `CustomersView`, revenue summary |
| States | loading, empty, error |

### 1.14 Leads

| Field | Spec |
|-------|------|
| Nav | `leads` |
| Data | `getLeads` + create/update |
| Components | `LeadsView`, lead form, status controls |
| States | loading, empty, error, saving |

### 1.15 Analytics

| Field | Spec |
|-------|------|
| Nav | `analytics` |
| Data | insights + activity + github |
| Components | `InsightsView`, `ActivityFeedView`, `GitHubSummary` |
| States | loading, empty insights, error |

### 1.16 Billing

| Field | Spec |
|-------|------|
| Nav | `billing` |
| Data | spend + cost control |
| Components | `BillingView`, `SpendDashboard`, `CostControlView` |
| States | loading, empty, error, cap-warning (if API provides) |

### 1.17 Settings

| Field | Spec |
|-------|------|
| Nav | `settings` |
| Data | health + executive deployment |
| Components | Split into clear sections: **Environment health**, **Deployment**, future **Account** (email display, sign out already in profile) |
| States | loading, error |
| Note | Do not pretend this is full account settings until prefs APIs exist — label honestly |

### 1.18 Overlays

| Surface | Components | Notes |
|---------|------------|-------|
| Command palette / search | `CommandPalette`, `GlobalSearchBar` | Map all nav targets; mobile open via icon |
| Notifications | `NotificationPanel` | Empty + error |
| Profile | `ProfileMenu` | Settings link, sign out |
| Mobile nav | `MobileNavDrawer` | Focus trap, close on navigate |

---

## 2. Component inventory (target architecture)

### 2.1 Foundations

- `ErrorBoundary`
- `Spinner` / `Skeleton` / `SkeletonPage`
- `EmptyState` (title, body, optional action)
- `ErrorState` (message + Retry)
- `StatusChip` (success | warning | danger | info | neutral)
- `Button` (primary | secondary | ghost | danger)
- `IconButton`
- `TextField`, `Select`, `TextArea`
- `Badge` (count)
- `Tooltip` (optional P2)

### 2.2 Layout

- `AppShell`, `Sidebar`, `TopBar`, `Main`, `PageHeader`
- `Stack`, `Cluster`, `Grid` (spacing via tokens only)
- `Surface` (single elevation language — avoid nested card-in-card)

### 2.3 Domain (keep; harden types)

- From `LumoraDashboard.tsx`: dashboard home, review queue, pipelines/workers wrappers, billing, settings layout  
- From `MissionControlV4.tsx`: ExecutiveMode, Timeline, LiveLogs, Assistant, Search  
- From `MissionControlPanels.tsx`: Activity, Content, Cost, Insights, QuickActions, SystemHealth, WorkerTimeline  

### 2.4 Deprecate / quarantine

- `OperationsDashboard.tsx` — do not extend; remove or mark `@deprecated` after shell parity  
- Legacy `.desk` CSS block — delete after confirming unused  

### 2.5 Navigation data contract (mandatory)

```
onNavigate(next):
  setLoading(true)
  setData(null)
  setError(null)
  setNav(next)
```

Render rule: `if (!loading && data && isX(data))` — never cast stale unions.

---

## 3. Design system

### 3.1 Principles

- One composition language: dark ops console, calm, high signal  
- **No purple-default AI look** — replace current `#9b87f5` accent  
- Brand “Lumora” must remain visible in shell (mark + wordmark); page H1 must not overpower brand in auth; interior pages use product name in sidebar, page title for task  
- Cards only where they group an interaction (Review Gate decisions); prefer lists/surfaces for read-only ops data  
- Human Review Gate wording preserved everywhere  
- Failures always visible; never empty catch without UI  

### 3.2 Color palette (target tokens)

Replace dual `:root` blocks with **one** token set:

| Token | Role | Proposed value |
|-------|------|----------------|
| `--paper` | App background | `#0B0F14` |
| `--panel` | Surface | `#121821` |
| `--panel-raised` | Elevated surface | `#18212C` |
| `--line` | Borders | `#2A3444` |
| `--ink` | Primary text | `#E8EEF6` |
| `--muted` | Secondary text | `#8B97A8` |
| `--accent` | Brand / focus | `#3D9B8F` (teal — distinct from mint desk + purple V1) |
| `--accent-soft` | Accent wash | `rgba(61, 155, 143, 0.14)` |
| `--success` | Healthy | `#3CB98A` |
| `--warning` | Warning | `#E0A23A` |
| `--danger` | Critical / reject | `#E45D6A` |
| `--info` | Informational | `#6B8CAF` |

**Severity rule:** Critical uses `--danger`; Warning uses `--warning`; never both as near-orange.

**Health footer mapping:**

- Any red subsystem → “Attention required” + danger  
- Only warnings → “Degraded” + warning  
- All green → “All systems operational” + success  

### 3.3 Typography

| Role | Family | Weight | Size / line |
|------|--------|--------|-------------|
| Brand / display | **Manrope** or **Sora** (pick one; drop Inter) | 700–800 | Auth H1 `clamp(2rem, 4vw, 2.75rem)` / 1.15 |
| UI headings | Same display family | 600–700 | H1 page `1.75rem`; H2 `1.15rem` |
| Body | **Source Sans 3** or **IBM Plex Sans** (not Inter) | 400–500 | `0.95rem` / 1.5 |
| Mono / IDs | **DM Mono** or **IBM Plex Mono** | 400 | `0.8rem` |

Load via `index.html` Google fonts (or self-host later). CSS variables:

```
--font-display
--font-body
--font-mono
```

### 3.4 Spacing scale

Use 4px base:

| Token | px |
|-------|-----|
| `--space-1` | 4 |
| `--space-2` | 8 |
| `--space-3` | 12 |
| `--space-4` | 16 |
| `--space-5` | 24 |
| `--space-6` | 32 |
| `--space-7` | 48 |
| `--space-8` | 64 |

**Layout constants:**

- Sidebar width: `248px` (desktop)  
- Top bar height: `64px`  
- Page padding: `24px` desktop / `16px` mobile  
- Surface radius: `12px`  
- Control radius: `8px`  
- Focus ring: `2px` accent, offset `2px`  

### 3.5 Icons

| Rule | Spec |
|------|------|
| Style | 24×24 viewBox, 1.75–2 stroke, round caps |
| Delivery | Single `icons.tsx` module (migrate `PATHS` out of dashboard) |
| Sizes | `16` inline · `18` nav · `20` metrics · `24` empty |
| Color | `currentColor` only |
| A11y | Decorative `aria-hidden`; actionable icons need `aria-label` on button |
| Set (minimum) | dashboard, mission, review, pipelines, workers, customers, leads, analytics, billing, settings, search, bell, menu, close, refresh, check, reject, alert, activity, chevron |

No emoji. No mixed icon libraries.

### 3.6 Elevation / surfaces

1. Flat page background (`--paper` + subtle radial teal wash ≤ 8% opacity)  
2. `Surface` — border `--line`, bg `--panel`  
3. Raised control / active nav — `--panel-raised` + accent soft wash  
4. **No** multi-layer drop shadows; optional single soft shadow `0 8px 24px rgba(0,0,0,0.35)` for drawers only  

---

## 4. Responsive behavior

| Breakpoint | Width | Behavior |
|------------|-------|----------|
| `sm` | &lt; 720px | Sidebar → drawer; hide search field, keep icon → palette; metric grid 2-col; review grid 1-col; stack health under activity |
| `md` | 720–1100px | Collapsible sidebar optional; metrics 3–4 col; review 2-col |
| `lg` | ≥ 1100px | Full sidebar; metrics up to 4–7 as designed; review 3-col; settings 2-col |

**Mobile rules:**

- Touch targets ≥ 44px for Approve/Reject  
- Profile name may hide; avatar remains  
- Notification + menu remain visible  
- No horizontal page overflow (`overflow-x` audit)  

---

## 5. Animations (intentional, 2–3 primary)

Ship **only** these product motions (plus reduced-motion cut):

1. **Nav active indicator** — 150ms ease accent wash on `SideNavItem`  
2. **Page enter** — content fade/slide `opacity 0→1` + `translateY(6px→0)` 180ms after load settles  
3. **Status pulse** — health footer / live badge soft pulse 2s (pause when degraded uses static danger)  

Optional P2: drawer slide 200ms; skeleton shimmer.

```css
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
```

---

## 6. State patterns (every screen)

| State | UI |
|-------|-----|
| Loading | Skeleton matching destination layout (not generic 6 blocks forever) |
| Empty | `EmptyState` with one sentence + optional CTA |
| Error | `ErrorState` with API message + Retry |
| Partial | Show loaded sections; failed section inline error (no silent omit) |
| Busy action | Disable control + `aria-busy` |

---

## 7. Accessibility requirements

- All inputs labeled (`<label>` or `aria-label`)  
- Sidebar `nav` landmark; main `main` landmark  
- Drawer focus trap + Escape  
- Color not sole severity signal (icon + text)  
- Contrast ≥ WCAG AA for body/muted on panels (raise `--muted` if needed)  
- Error boundary offers keyboard-reachable Reload/Retry  

---

## 8. Implementation work packages (post-approval)

| WP | Name | Touches | Depends |
|----|------|---------|---------|
| WP0 | Nav safety + ErrorBoundary + health footer truth | `LumoraDashboard.tsx`, small CSS | — |
| WP1 | Token / type / spacing consolidation | `app.css`, `index.html` | WP0 |
| WP2 | Auth form split + a11y labels | `App.tsx`, QuickActions | WP1 |
| WP3 | Dashboard metric/alert trust + mobile metrics | Dashboard views | WP1 |
| WP4 | Review Queue contrast + drawer a11y | Review components | WP1 |
| WP5 | Mission tabs hardening + re-screenshot | V4 views | WP0 |
| WP6 | Pipelines/Workers/Customers/Leads/Analytics/Billing empty states | Domain views | WP0–1 |
| WP7 | Deprecate `OperationsDashboard` + dead CSS | cleanup | WP5–6 |
| WP8 | Motion + reduced-motion | CSS | WP1 |

**Out of scope until separate CEO directive:** new product features, new APIs, marketing site, light theme, full account/settings prefs.

---

## 9. Acceptance criteria (for future implementation PR)

- [ ] Every nav item + Mission tab reachable without blank screen  
- [ ] Crash in one panel does not kill shell (error boundary)  
- [ ] Health footer matches worst subsystem status  
- [ ] Single design-token `:root`; no Inter; no purple accent  
- [ ] Login lacks workspace field; signup has it  
- [ ] Mobile 390px: no overflow; nav drawer works; review usable  
- [ ] Screenshots refreshed under `/tmp/cursor/artifacts/` for all screens in audit table  
- [ ] Vitest + lint + build green  

---

## 10. Explicit non-actions (this phase)

- Do **not** redesign visuals before WP0  
- Do **not** invent AI confidence on Review Gate without API field  
- Do **not** merge stacked PRs unless CEO asks  
