# Full-Stack Baseline Controlled Merge Plan

**Strategy:** protected GitHub PR merge commits, bottom-up  
**Direct push:** prohibited  
**Force push:** prohibited  
**Branch-protection bypass:** prohibited  
**Feature work during merge:** prohibited

## Preconditions

Before the first merge:

- Cumulative audit Critical = 0
- Cumulative audit High = 0
- Migration head = `0035`
- Fresh upgrade/downgrade/re-upgrade = pass
- Alembic check = pass
- API/worker/web/security/Docker gates = pass
- HRG and workspace isolation = pass
- All seven PRs are ready for review
- PR #43 head equals the cumulative audited SHA
- PR #43 has no commits after the audited SHA

## Repository merge strategy

Recent repository history uses two-parent merge commits for PRs. Use the GitHub
**Create a merge commit** action through the normal PR UI. Do not squash, rebase,
or merge locally unless repository owners explicitly change this policy.

## Exact bottom-up order

The stack must be merged one PR at a time:

1. **PR #36** — `cursor/operations-dashboard-v1-b52d` → `main`
2. Retarget **PR #37** to `main`; wait for its five checks; merge PR #37
3. Retarget **PR #38** to `main`; wait for its five checks; merge PR #38
4. Retarget **PR #39** to `main`; wait for its five checks; merge PR #39
5. Retarget **PR #40** to `main`; wait for its five checks; merge PR #40
6. Retarget **PR #41** to `main`; wait for its five checks; merge PR #41
7. Retarget **PR #43** to `main` only after #36–#41 are merged; verify its diff
   contains only the remaining top-of-stack commits; wait for five checks;
   merge PR #43

This is not the prohibited “retarget PR #43 directly to main” shortcut. PR #43
is retargeted only after every ancestor has landed in order.

PR #42 is not part of this release and must not be merged as part of this plan.

## Per-PR control loop

For each PR:

1. Confirm the current base and head SHA.
2. Confirm no unreviewed commit was added.
3. Confirm mergeability is clean.
4. Require all five checks:
   - API
   - Worker
   - Web
   - Security
   - Docker build
5. Merge through the protected GitHub PR UI using a merge commit.
6. Record the resulting `main` SHA.
7. Wait for the `push: main` CI workflow and require all five jobs.
8. Fetch `main` before retargeting the next child PR.
9. Confirm the child diff contains only its intended delta.

If any check fails, stop the stack. Do not continue with descendants.

## Final post-merge verification

After PR #43 merges:

1. Fetch `origin/main`.
2. Confirm `main:apps/web` equals the audited UI tree.
3. Confirm migrations `0034` and `0035` exist and head is `0035`.
4. Confirm full `main` CI: 5/5.
5. Run `scripts/ui_smoke_cdp.mjs` against a deployment built from `main`:
   - 16/16 surfaces
   - 0 blank/crash
   - 0 console errors/warnings
   - 0 uncaught exceptions
   - 0 footer/backend mismatches
   - alert parity true
6. Run `scripts/verify_hrg_isolation.mjs`:
   - HRG decision path passes
   - workspace isolation passes
   - backend health indicators present
7. Confirm no migration file changed during merge conflict resolution.
8. Publish the final `main` SHA and CI run.

## Agent authority boundary

The available PR tooling can mark ready, retarget, update descriptions, and
read CI, but it does not expose a merge action. The available GitHub CLI is
read-only for writes. Therefore a repository owner with merge permission must
click each protected merge in the order above unless a merge-capable protected
PR tool is provided.

The agent must stop at the first unavailable merge action; it must not emulate a
PR merge by pushing directly to `main`.

