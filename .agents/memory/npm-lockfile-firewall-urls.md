---
name: npm lockfile firewall URLs
description: npm installs inside Replit write package-firewall proxy URLs into package-lock.json, breaking GitHub Actions npm ci.
---

The rule: after any `npm install` / `npm audit fix` run inside the Replit
workspace, check `package-lock.json` for `package-firewall.replit.local`
resolved URLs and rewrite them to `https://registry.npmjs.org` before
pushing.

**Why:** Replit proxies npm through an internal firewall; the proxy URL
lands in the lock's `resolved` fields. GitHub Actions cannot resolve that
host, so `npm ci` fails with EAI_AGAIN. Integrity hashes are unchanged, so
a plain sed rewrite is safe.

**How to apply:** `grep -c package-firewall.replit.local package-lock.json`
after any npm dependency change; sed-replace and validate JSON before
committing.
