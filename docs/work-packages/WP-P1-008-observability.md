# P-008 / TD-037 — Observability + on-call baseline

## Objective

Expose scrapeable operational metrics and an on-call runbook without
introducing a new telemetry framework.

## Plan

1. Wire existing `orchestration/metrics.py` collectors to `GET /metrics`
   (Prometheus text; aggregate only).
2. Document on-call first-5-minutes in `docs/ops/ON_CALL.md`.
3. Tests for `/metrics` content-type and gauge presence.
4. Note: third-party OTel/Sentry exporters remain optional and need
   external credentials (out of scope for fail-closed in-repo work).

## Status — COMPLETE (in-repo baseline, 2026-07-28)

External APM vendor wiring still optional (credentials).
