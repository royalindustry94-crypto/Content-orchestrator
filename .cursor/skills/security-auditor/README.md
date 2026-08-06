# Security Auditor Skill — Documentation

**Skill id:** `security-auditor`  
**Location:** `.cursor/skills/security-auditor/`  
**Invoke:** `/security-auditor`

## Purpose

Independent security review before PR/release approval. Assumes unsafe until
proven otherwise. Covers authn/authz, RLS, worker credentials, secrets, CI,
spend/review bypass, races, and dependency/secret scans. Blocks on Critical
or High findings. Never merges. Never approves its own fixes without a fresh
full re-audit. VERIFIED requires factual evidence.

## Layout (Cursor best practices)

```text
.cursor/skills/security-auditor/
├── SKILL.md
├── README.md
├── references/
│   ├── audit-checklist.md
│   ├── threat-surfaces.md
│   ├── adversarial-rls.md
│   ├── ci-and-secrets.md
│   └── severity-guide.md
├── assets/
│   ├── security-audit-report-template.md
│   └── security-findings-template.md
└── scripts/
    └── security-audit-scan.sh
```

## How agents should use it

1. Identify branch, SHA, PR, migration head.
2. Follow the nine-step workflow in `SKILL.md` (restart after any fix).
3. Emit the required report template.
4. Status must be exactly VERIFIED, FAILED, or NOT VERIFIED.
5. Optional advisory: `bash .cursor/skills/security-auditor/scripts/security-audit-scan.sh`

## Related skills

| Skill | Role |
|---|---|
| `/postgresql-expert` | Schema/RLS design depth |
| `/backend-engineer` | Implements remediations |
| `/chief-architect` | Stack/SoT enabling insecurity |
| `/ceo` | Release VERIFIED; residual Medium acceptance |

## Related docs

- `.cursor/skills/AUTHORITY_MATRIX.md`
- `docs/SECURITY_AUDITOR_SKILL.md`
