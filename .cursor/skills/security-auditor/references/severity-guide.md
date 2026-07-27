# Severity guide

| Severity | Definition | Examples | Gate |
|---|---|---|---|
| **Critical** | Immediate tenant breach, auth bypass, or secret exposure in prod path | Cross-workspace data read; unauthenticated admin; plaintext secret in repo used in prod | Block |
| **High** | Likely exploit with moderate effort; financial or review integrity break | Spend race exceeding cap; review gate skip; revoked worker still privileged | Block |
| **Medium** | Real weakness needing fix/track; exploit less direct | Missing rate limit on claim; action not SHA-pinned; verbose errors in staging config | Track; CEO may CONDITIONAL accept with residual note |
| **Low** | Defense-in-depth / hardening | Missing security headers doc; overly broad CORS in dev-only | Track |
| **Informational** | Observation without direct exploit | Tooling unavailable; suggested monitoring | Note |

## Ranking rules

- Prefer **higher** severity when uncertain between two levels for isolation/financial/credential issues
- Do not lower severity because a fix is hard
- Multiple Mediums that combine into a practical exploit chain → raise to High
