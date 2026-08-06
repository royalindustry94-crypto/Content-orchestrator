# QA Breaker Skill — Documentation

**Skill id:** `qa-breaker`  
**Location:** `.cursor/skills/qa-breaker/`  
**Invoke:** `/qa-breaker`

## Purpose

Independent adversarial QA: try to break every in-scope feature before
approval. Real PostgreSQL only; concurrency/recovery/migration/frontend
gates; reject weak tests; evidence before VERIFIED; never merge; full
restart after fixes.

## Layout

```text
.cursor/skills/qa-breaker/
├── SKILL.md
├── README.md
├── references/
│   ├── attack-matrix.md
│   ├── test-quality.md
│   ├── concurrency-recovery.md
│   ├── migrations-qa.md
│   └── frontend-qa.md
├── assets/
│   ├── qa-breaker-report-template.md
│   ├── attack-matrix-template.md
│   └── qa-defect-template.md
└── scripts/
    └── qa-breaker-gate.sh
```

## Related skills

`/security-auditor` · `/postgresql-expert` · `/backend-engineer` · `/chief-architect` · `/ceo`

See `.cursor/skills/AUTHORITY_MATRIX.md` and `docs/QA_BREAKER_SKILL.md`.
