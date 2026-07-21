---
name: GitHub push auth for this repl
description: How to push to GitHub from this workspace — Replit credential helper is broken, use the PAT secret
---

# GitHub push auth

**Rule:** Push via shell git with the PAT secret, never via the `gitPush` callback or Replit's credential helper:

```bash
git push "https://${GITHUB_PERSONAL_ACCESS_TOKEN}@github.com/royalindustry94-crypto/Content-orchestrator.git" main 2>&1 | sed "s/${GITHUB_PERSONAL_ACCESS_TOKEN}/***/g"
```

**Why:** Replit's git credential helper times out ("GitHub token request timed out") in this workspace even after the user reconnected GitHub on replit.com/account. Both the `gitPush` callback and the Git pane fail with misleading PUSH_REJECTED errors. A classic PAT stored as the `GITHUB_PERSONAL_ACCESS_TOKEN` secret works.

**How to apply:** Any push/pull needing auth → use the PAT URL form above, always masking the token in output with sed. Verify pushes landed with `git fetch && git status -sb`.

## Gotchas learned the hard way

- The `gitPush` callback resolves the branch from HEAD, not its `branch` arg. If HEAD is on a different branch (e.g. a backup branch), it fails with "current branch already tracks X; cannot publish main". Always `git checkout main` first and confirm with `git symbolic-ref HEAD`.
- Pushes touching `.github/workflows/*` require the `workflow` scope on classic PATs. The current PAT (2026-07-21) has `repo,workflow` and ci.yml is pushed. If a future token swap drops `workflow`, such pushes fail with "refusing to allow a Personal Access Token to create or update workflow".
- Fine-grained PATs (no `x-oauth-scopes` response header) default to read-only on public repos — symptom: reads succeed, push gets 403 "Permission denied to <owner>". Ask for a classic token with explicit scopes instead.
