# DevOps PR notes (template)

## Summary
<!-- CI/CD or deploy reliability change -->

## Workflows / jobs touched
<!-- permissions changes called out -->

## Migration / rollback
<!-- head, up/down or expand/contract, rollback steps -->

## Secrets / env
<!-- no secrets in git; list new required env vars -->

## Test plan
- [ ] GitHub Actions green on this SHA
- [ ] Advisory: `bash .cursor/skills/devops-engineer/scripts/devops_gates.sh` (optional local)

## Status
VERIFIED | FAILED | NOT VERIFIED

## Do not merge
DevOps Engineer does not merge. Requires human/CEO after QA + Security as applicable.
