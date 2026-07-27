# Cursor Skills (Content Orchestrator)

Project skills live under `.cursor/skills/<skill-id>/` with a required
`SKILL.md` (see [Cursor Skills docs](https://cursor.com/docs/skills.md)).

## Installed skills

| Skill | Invoke | Purpose |
|---|---|---|
| [`postgresql-expert`](./skills/postgresql-expert/) | `/postgresql-expert` | PostgreSQL schema, RLS, migrations, performance, concurrency |
| [`backend-engineer`](./skills/backend-engineer/) | `/backend-engineer` | FastAPI/SQLAlchemy implementation (see PR if not on branch) |
| [`chief-architect`](./skills/chief-architect/) | `/chief-architect` | Architecture protection (see PR if not on branch) |
| [`ceo`](./skills/ceo/) | `/ceo` | CEO — product/quality/release (see PR if not on branch) |

## Adding a skill

1. Create `.cursor/skills/<kebab-name>/SKILL.md`
2. Set frontmatter `name` to the **same** kebab-case folder name
3. Write a precise `description` (used for relevance matching)
4. Put long material in `references/`; scripts in `scripts/`; templates in `assets/`
5. Document the skill in its own `README.md`
