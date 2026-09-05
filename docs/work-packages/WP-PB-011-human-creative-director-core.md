# WP-PB-011 — Human Creative Director Core

**Product:** The Business Manager

**Status:** development candidate; provider activation and publication remain blocked

## Outcome

A customer can describe an image, video, cartoon, or animation in ordinary
language. A human operator can turn that brief into a provider-neutral prompt
pack, record continuity and negative-prompt rules, and obtain explicit approval
of the exact prompt-pack fingerprint before any paid generation is attempted.

## Smallest shippable scope

- Workspace-scoped creative projects.
- Immutable, fingerprinted creative brief revisions.
- Immutable, fingerprinted prompt-pack revisions tied to the latest brief.
- Exact-fingerprint approve or request-changes decisions by an admin/reviewer.
- Automatic invalidation of an earlier approval when a newer prompt pack exists.
- Structured audit events for project, brief, prompt-pack, and decision writes.
- Member reads, admin/editor authoring, and admin/reviewer decisions.

## Non-goals

- No image, video, voice, or animation provider calls.
- No provider credentials or browser-side secrets.
- No media upload or object storage.
- No cost estimate presented as a guaranteed saving.
- No automatic approval, final-content approval, or external publishing.
- No replacement for the existing mandatory final Human Review Gate.

## Trust boundaries

- Every table is workspace-scoped with database-enforced same-workspace foreign
  keys, ENABLE RLS, FORCE RLS, and least-privilege runtime policies.
- Briefs, prompt packs, and decisions are append-only.
- A decision references the exact prompt-pack ID and fingerprint through a
  composite database foreign key.
- Only the latest prompt-pack revision can be decided.
- Generation-plan approval is not publication approval.
- This slice has no provider side effect and therefore reserves no spend.

## Acceptance evidence

- Alembic has one head at `0053`.
- Upgrade, downgrade to `0052`, re-upgrade, full replay, FORCE RLS inventory,
  policy inspection, and foreign-key index checks pass on a disposable local
  database ending `_test`.
- API tests prove exact-fingerprint approval, wrong/stale fingerprint rejection,
  new-revision invalidation, role enforcement, outsider denial, and direct RLS
  invisibility across all four new tables.
- API Ruff, full pytest with coverage, security, Docker, web, worker, and browser
  smoke pass on the exact candidate SHA.
- An independent auditor delivers a verified PDF before merge consideration.

## Implementation order and rollback

1. Add migration and ORM mappings.
2. Add bounded schemas and provider-neutral service rules.
3. Add authenticated routes and structured audit events.
4. Add adversarial tests and exact-head CI evidence.

Downgrading `0053` drops all Human Creative Director planning history and is
data-destructive. It is acceptable only before customer use or after an
authorized backup/export. Application rollback should normally leave the
forward-compatible tables in place.

## Open decisions

- The first live generation provider is deliberately undecided.
- Media upload/storage and pricing are separate Founder-approved milestones.
- Cursor owns the customer/operator UI; Copilot owns assurance automation.
