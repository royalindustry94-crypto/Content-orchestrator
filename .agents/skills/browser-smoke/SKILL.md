---
name: browser-smoke
description: Verify Business Manager user journeys in a real browser after web, API contract, onboarding, review, or responsive-layout changes.
---

# Browser Smoke

Use a local or explicitly approved preview environment. Do not enter real customer credentials or trigger external publishing.

1. Confirm API and web readiness before opening the browser.
2. Seed only documented test data.
3. Exercise the changed journey at desktop width and 390px mobile width.
4. Check for blank screens, crashes, console errors, horizontal overflow, unlabeled controls, keyboard traps, missing focus state, and sub-44px primary touch controls.
5. Verify truthful unavailable/provider-not-configured states; never accept a silent placeholder as success.
6. For content flows, confirm the result enters Human Review and nothing publishes externally.
7. Prefer resilient role/label locators. Do not depend on arbitrary sleeps when readiness or visible-state assertions are available.

Use `scripts/ui_smoke_cdp.mjs` for the existing full navigation smoke. If Playwright is introduced later, keep the same behavioral assertions and preserve screenshots/logs as evidence. Report tested URL, viewport, exact SHA, route results, console results, and artifact location.
