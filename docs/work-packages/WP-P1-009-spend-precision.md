# P-009 / TD-022 — Spend cap Numeric precision

## Objective

Allow sub-cent spend caps (e.g. `0.005`) without silent rounding to
`0.01`, aligning cap scale with estimate/ledger `numeric(10,4)`.

## Plan

1. Alembic `0031_spend_precision`: `spend_caps` daily/monthly → `numeric(12,4)`.
2. ORM `Numeric(12, 4)`; API schema Decimal with `decimal_places=4`.
3. Tests: preserve `0.005`; reject 5+ decimal places.
4. Docs + TD-022 close.

## Rollback

`alembic downgrade 0030` rounds caps back to `numeric(10,2)` (sub-cent
values lose precision by design).

## Status — COMPLETE (2026-07-28)
