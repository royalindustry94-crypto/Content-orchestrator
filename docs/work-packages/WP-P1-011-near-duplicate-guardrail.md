# WP-P1-011 — Near-duplicate content guardrail

**Status:** proposed, not implemented.
**Origin:** `docs/EXTERNAL_REPO_RESEARCH_2026-09.md` — closes the
"Duplicate / repetitive-content guardrail" row marked **CONFIRMED OPEN**
in `docs/PLATFORM_POLICY_CONTROL_MATRIX.md`.
**Blocked by:** nothing — does not touch `PROVIDER-001` (no live
provider call), `PUBLISH-001` (no external publish), or `BILLING-001`.

## Problem

`apps/api/app/services/content_department.py` (`_fingerprint`,
`_structure_fingerprint`, and the originality check around lines
465–500) only detects **exact** duplicates: SHA-256 of the
lowercased, whitespace-collapsed script body/hook/CTA. Changing one
word anywhere defeats it. `docs/PLATFORM_POLICY_CONTROL_MATRIX.md`
requires the guardrail to survive "superficial edits" — it doesn't
today.

## Proposed approach

Add a 64-bit SimHash of the script body (public, well-known algorithm:
token-shingle → hash → weighted bit vector → majority sign per bit).
No new dependency — implement and unit-test it directly; it's ~30
lines and the whole point is to control the similarity threshold and
false-positive behavior ourselves rather than take it from an
unaudited library.

1. Compute `simhash_hex = simhash(script_body)` alongside the existing
   `_fingerprint` calls.
2. Store it in `OriginalityFingerprint.semantic_reference` (column
   already exists, currently always `None` — no migration needed).
3. On each new fingerprint, compare `simhash_hex` (Hamming distance)
   against other fingerprints in the same workspace via
   `semantic_reference`. Suggested thresholds (tune with real data
   before shipping): Hamming distance ≤ 3 of 64 bits → treat as
   near-duplicate at the same severity as today's exact-match path
   (`audited_blocked` / `state="blocked"`); 4–10 bits → add a
   `medium`/`"flagged"` finding surfaced to the reviewer but
   non-blocking, so the Human Review Gate sees it without a new
   auto-block class that hasn't been proven safe against false
   positives.
4. Add adversarial unit tests: same script with synonym swaps, reordered
   sentences, inserted filler, and a control set of genuinely distinct
   scripts on the same topic that must **not** trip the near-duplicate
   path (false-positive check matters as much as the true-positive
   check here).
5. Update `docs/PLATFORM_POLICY_CONTROL_MATRIX.md`'s row from
   CONFIRMED OPEN to reflect the new evidence once tests land, and add
   a `docs/architecture-decisions.md` entry recording the threshold
   choice and why (mirrors the existing entries' style).

## Explicitly out of scope for this WP

- Any ML/embedding-based semantic similarity (would need a live model
  call — that's `PROVIDER-001` territory).
- Changing the exact-duplicate path's existing blocking behavior.
- Cross-workspace comparison (would break workspace isolation —
  comparisons must stay scoped to `workspace_id`, matching every other
  query in this file).

## Review requirement

Per `AGENTS.md`'s milestone governance, this touches a compliance/
audit-relevant path — implement it, then get an independent pass
(second AI reviewer or adversarial audit against fresh evidence) before
treating the control-matrix row as closed. The implementing agent
should not be the sole certifier of "cannot be evaded by superficial
edits" for its own change.
