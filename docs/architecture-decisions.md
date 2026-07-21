# Architecture Decisions

## Source-of-truth spec

`content_engine_app_spec_v2.md` + the Claude Project Instructions doc are
authoritative. `lovable_app_spec_369.md` ("TeslaFlow 369") was reviewed and
**rejected** — see below.

## Why the 369 spec was rejected

The 369 doc hard-codes Tesla 3-6-9 numerology into product constraints with
no engineering rationale: content pillars capped at 3, exactly 9 visuals per
video, keyword counts fixed at 3/6/9, publish times restricted to 3:00 /
6:00 / 9:00, batch sizes fixed at 3/6/9.

This directly conflicts with the real requirements:

- **Scale target** (v2 spec, carried into project instructions): up to
  **5** content pillars, 50 videos/day peak. Incompatible with a hard cap
  of 3 pillars.
- **Roles**: the mandatory Human Review Gate needs its own `reviewer` role
  (admin/editor/reviewer). The 369 spec only has admin/editor.
- **Configurability**: v2 explicitly states its numbers are defaults, not
  hard constraints. Every count in this system (pillars, visuals, keywords,
  batch sizes, schedule presets) is a configurable value, not a fixed one.

None of the 369 spec's constraints are implemented. If a future request
references "the 369 spec," confirm before building against it.

## Data store

Postgres only for v1 (structured data + logs/events). The 369 spec's
"potentially NoSQL for logs" suggestion was not adopted — no second
datastore without a concrete scale reason.

## Workspace scoping

Single workspace per account at launch (v2 spec). Every tenant-owned table
carries `workspace_id` via `WorkspaceScopedMixin` (see `apps/api/app/db/base.py`)
so this can't be omitted on a new model.
