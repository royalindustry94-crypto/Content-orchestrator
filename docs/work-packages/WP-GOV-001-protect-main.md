# WP-GOV-001 — Protect `main` Branch

**Status:** IN PROGRESS  
**Issue:** #50  
**Severity:** HIGH  
**Owner:** Founder  

---

## Objective

Technically enforce that `main` can only receive code that has passed all six
CI gates and arrived via a reviewed pull request.  Currently `main` is
unprotected (no required status checks, no PR requirement, force-pushes
allowed).

---

## Required protection settings

| Setting | Required value |
|---------|---------------|
| Require pull request before merge | ✅ enabled, 1 approving review |
| Dismiss stale PR approvals on new push | optional (recommended) |
| Required status checks (strict — branch must be up to date) | `api`, `worker`, `web`, `security`, `docker-build`, `browser-smoke` |
| Enforce branch-up-to-date before merge | ✅ (`strict: true`) |
| Enforce admins | ✅ (no bypass for routine pushes) |
| Allow force pushes | ❌ blocked |
| Allow deletions | ❌ blocked |

Emergency bypass: Founder only, must be documented before/after each use.

---

## Implementation

### Option A — Run the provided workflow (recommended)

1. Add a **repository secret** named `ADMIN_PAT` containing a GitHub Personal
   Access Token with `admin:repo` (or classic `repo`) scope, owned by a
   repository admin account.
2. Go to **Actions → Apply main branch protection → Run workflow**.
3. Leave `dry_run` unchecked and click **Run workflow**.
4. The workflow applies the protection payload and then re-reads the branch
   endpoint to verify all gates are active.  The job will fail if any
   required check is missing.

### Option B — GitHub web UI (manual)

1. Repository **Settings → Branches → Add rule**.
2. Branch name pattern: `main`.
3. Check **Require a pull request before merging** (1 required approval).
4. Check **Require status checks to pass before merging**, enable strict, and
   add: `api`, `worker`, `web`, `security`, `docker-build`, `browser-smoke`.
5. Check **Do not allow bypassing the above settings**.
6. Uncheck **Allow force pushes** and **Allow deletions**.
7. Save.

### Option C — GitHub REST API (curl)

```bash
curl -X PUT \
  -H "Authorization: ******" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/royalindustry94-crypto/Content-orchestrator/branches/main/protection" \
  -d @docs/work-packages/branch-protection-payload.json
```

---

## Verification (independent auditor)

After applying protection, the auditor must execute:

```bash
curl -H "Authorization: ******" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/royalindustry94-crypto/Content-orchestrator/branches/main" \
| python3 -c "
import json, sys
d = json.load(sys.stdin)
print('protected:', d.get('protected'))
print('checks:', d.get('protection',{}).get('required_status_checks',{}).get('contexts'))
print('enforce_admins:', d.get('protection',{}).get('enforce_admins',{}).get('enabled'))
print('force_push_allowed:', d.get('protection',{}).get('allow_force_pushes',{}).get('enabled'))
"
```

Expected output:
```
protected: True
checks: ['api', 'worker', 'web', 'security', 'docker-build', 'browser-smoke']
enforce_admins: True
force_push_allowed: False
```

Record the full JSON blob and the git SHA of `main` at the time of
verification as evidence in the next milestone audit.

---

## Acceptance criteria

- [ ] `GET /branches/main` returns `protected: true`.
- [ ] All six status checks (`api`, `worker`, `web`, `security`, `docker-build`,
      `browser-smoke`) appear in `required_status_checks.contexts`.
- [ ] `enforce_admins.enabled: true`.
- [ ] `allow_force_pushes.enabled: false`.
- [ ] `allow_deletions.enabled: false`.
- [ ] Independent auditor records evidence and updates `docs/LAUNCH_BLOCKERS.md`
      to close GOV-001.
