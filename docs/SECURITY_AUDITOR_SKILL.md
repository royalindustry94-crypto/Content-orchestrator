# Security Auditor Skill

Independent security audit skill for Content Orchestrator.

| | |
|---|---|
| **Invoke** | `/security-auditor` |
| **Package** | [`.cursor/skills/security-auditor/`](../.cursor/skills/security-auditor/) |
| **Guide** | [`.cursor/skills/security-auditor/README.md`](../.cursor/skills/security-auditor/README.md) |
| **Authority** | [`.cursor/skills/AUTHORITY_MATRIX.md`](../.cursor/skills/AUTHORITY_MATRIX.md) |

## Responsibilities

- Independent reviewer (not the implementer)
- Authn/authz, JWT, RLS, workspace isolation, worker credentials
- Adversarial Postgres RLS tests; secret/CI/dependency scans
- Human Review Gate and spend-control bypass resistance
- Block on Critical/High; regression tests required
- Fresh re-audit after fixes; evidence before VERIFIED; never merge

## Advisory scan

```bash
bash .cursor/skills/security-auditor/scripts/security-audit-scan.sh
```
