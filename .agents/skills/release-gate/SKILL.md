---
name: release-gate
description: Verify whether an exact Business Manager branch or pull request is safe to merge or deploy after implementation is complete.
---

# Release Gate

This skill verifies readiness; it does not grant permission to merge or deploy.

1. Identify local HEAD, remote head, PR head, base, tree identity, and migration head. Explain any mismatch.
2. Confirm the diff matches the approved work package and contains no unrelated or generated secrets.
3. Run `scripts/agent-check.sh full` and preserve its evidence directory.
4. Require exact-head success for the repository's hosted jobs: `api`, `worker`, `web`, `browser-smoke`, `security`, and `docker-build`.
5. Reconcile unresolved audit findings and documentation claims with the code and live GitHub state.
6. For deployment readiness, separately verify managed database migrations, authentication, backups, environment secrets, health checks, and rollback. Code CI is not hosted-runtime proof.

Return one outcome:

- **MERGE READY**: exact-head evidence is complete and blocking findings are closed.
- **NOT MERGE READY**: a required check failed, did not run, used another SHA, or safety evidence is unknown.
- **DEPLOY READY** only when hosted runtime evidence also exists.

Never merge, deploy, dismiss findings, or weaken a required check as part of verification.
