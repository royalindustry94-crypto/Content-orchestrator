# The Business Manager — Master Change Brief Reconciliation

## Scope

This record applies the attached **Master Change Brief — No Circles** to the disposable, zero-cost Founder Preview only. It does not authorize a merge, public deployment, live billing, automatic external publishing, or any change to backend tenancy, Human Review Gate, spend, recovery, provider, or worker-control contracts.

## Implemented preview changes

| Brief direction | Preview implementation |
|---|---|
| Approved identity | The superseded TB mark was replaced by the silver upward geometric chevron with a gold inner chevron. The canonical stacked wordmark is used on the authentication screen; a legible compact SVG chevron is used in navigation and favicon contexts. |
| Authentication first | A fresh session reaches the near-black centered sign-in screen before Home. Email/password login and account creation retain existing local-auth behavior. |
| Authentication controls | Email, Password, Remember me, Forgot password, SIGN IN, and account creation appear in the approved hierarchy. Remember me is visibly unavailable because secure revocable refresh sessions and device management are not implemented; it does not store passwords. Recovery is also explicitly unavailable. Google continuation is omitted because no supported provider path exists. |
| No-circles Business Performance | The Home page uses a simple four-metric availability grid: Revenue, Spending, Net profit, and Profit margin. Each is `Not connected` and `Source-backed data required` until a financial source is available. No circular chart, donut, pie graph, or synthetic financial value remains on Home. |
| Home hierarchy | Home prioritizes Business Performance, What Needs You, Ask My Business, AI Workforce, activity, and insights. |
| Ask My Business | Home and a dedicated Ask route use the outcome-first phrase `What do you want sorted?`. The existing workspace-scoped assistant endpoint remains the only request path. The preview does not claim automatic worker selection, external execution, or publishing. |
| Navigation | The owner-facing order begins Home, Ask, Opportunities, Content, Human Review, Workforce, Money, and Insights. Existing Audience, Connections, and Settings routes remain available. |

## Explicitly deferred

The following are not implemented and must remain visibly unavailable rather than simulated: connected revenue/expense ledger, reconciled profit and margin, Business Brain context model, secure refresh-token/session revocation/device management, password recovery, Google sign-in, full workforce role bindings/executors, independent audit-view records, official engagement integrations, deals, and rate intelligence.

## Validation evidence

| Check | Result |
|---|---|
| Frontend lint, tests, production build | Passed: 26 tests across 4 files; TypeScript/Vite build passed. |
| Live desktop/browser smoke | Passed: 17 exercised route states; 0 blank/crash states; backend alert/footer parity true. |
| Exact 390px mobile smoke | Passed: 3 supplemental states; 0 failures; no horizontal overflow. |
| Browser safety | 0 console warnings/errors; 0 uncaught exceptions; 0 unlabeled controls. |
| No-circles audit | Passed: no circular financial selector or conic-gradient remains in production frontend source; Home verifies four unavailable source-backed metrics. |
| Tenant, Human Review, spend, and preview security | Passed: 17 targeted backend regression tests. |
| Tokenless metrics | Preserved: 401. |
| Direct-entry removal | The temporary direct-entry middleware was removed; the old route resolves only to the Vite SPA fallback and has no session payload. |

## Approval gate

Founder visual approval is still required. The preview is intentionally **blocked from production authentication readiness** until secure revocable session/refresh token handling, device/session management, logout revocation, and supported password-recovery behavior are designed and implemented. These limitations are explicit in the preview and do not weaken the existing session-scoped login flow.
