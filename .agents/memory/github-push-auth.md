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
- The user's PAT lacks the `workflow` scope, so pushes touching `.github/workflows/*` are rejected by GitHub. As of 2026-07-21, `.github/workflows/ci.yml` exists locally but is **untracked/unpushed** for this reason. To push it: user must mint a token with `repo,workflow` scopes (github.com/settings/tokens/new?scopes=repo,workflow), or add the file via GitHub web UI.
- Fine-grained PATs (no `x-oauth-scopes` response header) default to read-only on public repos — symptom: reads succeed, push gets 403 "Permission denied to <owner>". Ask for a classic token with explicit scopes instead.
