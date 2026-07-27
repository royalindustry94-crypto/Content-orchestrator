# Deploy / CI checklist

## Pre-merge / pre-deploy

- [ ] Diff reviewed for workflow permissions and secrets
- [ ] `.github/workflows/ci.yml` still covers api + worker + web as applicable
- [ ] Actions green on SHA
- [ ] Migration head cited; upgrade path known
- [ ] Rollback steps written
- [ ] Worker restart / lease recovery considered
- [ ] Health/readiness/shutdown known or ticketed to Backend
- [ ] No Review Gate / spend bypass
- [ ] Security findings: none Critical/High open (or FAILED)

## Evidence to paste

- [ ] PR URL
- [ ] Commit SHA
- [ ] Actions run URL
- [ ] Migration revision id
- [ ] Rollback notes
- [ ] Residual risks

## Status

VERIFIED | FAILED | NOT VERIFIED
