# Codex task - Human-Finished Creative Core

Use Lane 1 in `.agents/coordination/THREE_LANE_WORKSPACE.md`.

The smallest first slice imports externally created media without connecting a
generation provider. Design and implement metadata, immutable revisions,
workspace-safe lineage, validation state, human notes and exact-artifact Human
Finished approval. Preserve the current review gate and disabled publishing.

Before schema work, use the milestone-plan and safe-migration skills. Require
same-workspace references at the database boundary, FORCE RLS, covering
indexes, upgrade/downgrade evidence, outsider and cross-workspace negatives,
and approval invalidation when the artifact checksum changes. Do not store
media bytes in PostgreSQL and do not activate object storage or credentials in
this slice.

Commit only on the Codex lane branch and publish a structured handoff. Do not
merge or deploy. Any audit result must be a verified downloadable PDF outside
Git.

Before the media slice, close and regression-test the current audit findings:

- refuse approval when the gate's content version is no longer current;
- default-deny every worker stage except the explicitly supported allowlist;
- fail closed when a chargeable successful stage has no spend reservation;
- move tenant hot-path reads toward the RLS runtime session where policy allows;
- harden staging bootstrap so special characters in runtime passwords are not
  interpolated into shell source text.
