# Phase 1 — Dependency Verification Report

Purpose (per amendment 2): before deleting anything, prove no remaining
file references scaffold components or removed modules — no broken imports,
no orphaned config.

## Method

Static scan of the foundation tree: every internal (`app.*`, `worker.*`)
import resolved against files on disk; every external import checked
against declared dependencies; targeted greps for scaffold-stack tokens
and for removed Milestone-3 modules.

## 1. Internal import graph — all resolve

17 distinct `app.*` import targets; **all 17 resolve** to an existing
module or package. No dangling internal imports.

```
app.main
 ├─ app.api.routes.health      → app.db.session
 ├─ app.api.routes.profiles    → app.core.security, app.models.profile, app.schemas.profile
 ├─ app.api.routes.workspaces  → app.core.authorization, app.core.security,
 │                               app.models.workspace, app.models.workspace_membership,
 │                               app.schemas.workspace
 ├─ app.api.routes.memberships → app.core.authorization, app.core.security,
 │                               app.models.profile, app.models.workspace_membership,
 │                               app.schemas.membership
 ├─ app.core.config
 └─ app.core.logging

app.core.security      → app.core.config, app.db.session
app.core.authorization → app.core.security, app.models.workspace_membership
app.db.session         → app.core.config
app.db.base            → (sqlalchemy only)
app.models.*           → app.db.base
app.schemas.*          → app.models.workspace_membership (enum reuse)

worker.main → worker.core.config, worker.core.logging
```

## 2. External dependencies — all declared

Third-party imports referenced in `apps/api`: `fastapi`, `pydantic`,
`pydantic_settings`, `sqlalchemy`, `jose`. **All present** in
`apps/api/pyproject.toml`. Remaining imports are Python stdlib
(`collections`, `contextlib`, `dataclasses`, `datetime`, `enum`,
`functools`, `json`, `logging`, `sys`, `time`, `typing`, `uuid`).

No reference to any Node/Drizzle/Express package. No undeclared
third-party import.

## 3. Removed-module reference scan — zero orphans

After removing the in-progress Milestone-3 files, scanned for any
surviving reference to them:

- `app.models.{config,content,pipeline,delivery,history,spend,operations,enums}` → **none**
- M3 mixins (`CreatedAtMixin`, `ActorMixin`, `VersionMixin`, `SoftDeleteMixin`, `CreatedByMixin`) → **none**
- `migration_helpers` → **none**

`app/models/__init__.py` exports only `Profile`, `Workspace`,
`WorkspaceMembership`, `WorkspaceRole`. `alembic/env.py` imports
`app.models`, which now registers only the three M2 tables — so
`alembic upgrade head` and autogenerate see exactly the M2 schema, no
missing-table or extra-table drift.

## 4. Scaffold-token scan — clean

`grep -rniE '(express|drizzle|app\.listen|require\(|module\.exports)'`
over `apps/api` and `apps/worker`: **no matches**. No backend `*.ts`/`*.js`.
Only `package.json` in the tree is `apps/web/package.json` (the frontend).

## 5. Compilation

`python -m py_compile` over every `.py` in `apps/api` and `apps/worker`:
**all compile**. (Runtime import execution and the test suite require the
third-party packages, which install in CI — see the can't-run note in the
architecture doc.)

## Conclusion

No file in the foundation references a scaffold component or a removed
module. Safe to proceed: broken-import / orphaned-config risk is cleared.
