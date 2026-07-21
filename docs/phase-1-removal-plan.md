# Phase 1 — Repository Recovery: Removal Plan (FOR REVIEW — nothing deleted yet)

## Situation

The GitHub repository currently holds a **Replit scaffold** — a
Node/Express/Drizzle/Vite starter — not the approved Milestone 2
implementation, which was never committed. The approved Milestone 2 code
exists as a verified implementation (FastAPI / Python / SQLAlchemy /
Alembic / Supabase Auth) ready to become the authoritative foundation.

Recovery is therefore not a surgical edit of the scaffold — it's a
**stack replacement**: the scaffold is the wrong language and framework
entirely. This plan classifies every category of scaffold artifact as
REMOVE / KEEP / REVIEW, per the directive to remove only scaffold code
that conflicts with the approved architecture and preserve useful
infrastructure. No file is deleted until this plan is approved.

Because I can't reach GitHub from here, the scaffold inventory below is
expressed by the categories a Replit Node scaffold contains. On approval,
the actual removal executes against whatever matches these categories in
the real repo — I'll reconcile any item not listed here before deleting
it, not delete blind.

## Classification

### REMOVE — conflicts directly with the approved architecture

| Scaffold artifact (typical path) | Why it conflicts | Replaced by |
|---|---|---|
| `package.json`, `package-lock.json` (root, backend) | Declares a Node/Express backend; approved backend is Python/FastAPI | `apps/api/pyproject.toml` |
| `server/` / `index.ts` / `app.ts` (Express server) | Express is explicitly NOT the stack | `apps/api/app/main.py` (FastAPI) |
| `drizzle.config.ts`, `drizzle/`, `db/schema.ts` | Drizzle ORM is explicitly NOT the stack | SQLAlchemy models + Alembic migrations |
| `vite.config.ts` at repo root serving the backend | Vite-as-backend is explicitly NOT the stack | FastAPI serves the API; Vite stays only as the **frontend** dev tool under `apps/web` |
| `tsconfig.json` (root, backend-oriented) | TypeScript backend config | n/a (backend is Python); a separate tsconfig lives under `apps/web` |
| `.replit`, `replit.nixmod`, `replit.nix` | Replit-runtime lock-in; deployment target is Supabase/containers | `docker-compose.yml` + CI |
| `node_modules/` (if committed) | Never belongs in git | `.gitignore` already excludes it |
| Express auth middleware / custom JWT signing (if any) | Violates "Supabase owns auth; FastAPI only verifies; never custom auth" | `apps/api/app/core/security.py` (verify-only) |
| Scaffold demo routes / sample CRUD (`routes/example.ts` etc.) | Placeholder business logic | Real M2 routes (`/me`, workspaces, memberships) |

### KEEP — useful infrastructure, stack-agnostic

| Artifact | Condition |
|---|---|
| `.gitignore` | Keep, but **merge** — ensure it covers Python (`__pycache__/`, `.venv/`, `*.pyc`, `.ruff_cache/`, `.pytest_cache/`) as well as Node. The approved repo's `.gitignore` already does; reconcile the two rather than dropping either. |
| `.github/workflows/` CI | Keep the *directory/CI habit*, but **replace contents** — the scaffold's CI runs `npm`/Node steps that don't apply. The approved `ci.yml` (Postgres service + `alembic upgrade head` + `pytest` + `ruff`, plus the web lint/build job) supersedes it. |
| `README.md` | Replace content (scaffold readme describes the wrong stack), keep the file. |
| `LICENSE`, `.editorconfig`, `.gitattributes` (if present) | Keep as-is — genuinely stack-agnostic. |
| Any `docs/` that predates the scaffold and is still accurate | Review case-by-case (§REVIEW). |

### REVIEW — decide before acting

| Artifact | Question for you |
|---|---|
| `.env` / `.env.example` from the scaffold | Almost certainly Node var names. Approved `.env.example` replaces it — but confirm there are no real secrets committed in a scaffold `.env` that need rotating (see audit note below). |
| `apps/web` frontend scaffold, if the Replit starter had a React app | The approved repo has a minimal `apps/web` (Vite + React + TS) wired to the API health check. If the scaffold's frontend has anything worth keeping (design, components), flag it; otherwise the approved `apps/web` stands and the scaffold frontend is removed. |
| Git history itself | The scaffold commits are in history. Options: (a) keep history and commit the foundation on top; (b) squash/orphan to make the foundation the first real commit. Recommend (a) — preserves the audit trail that the scaffold existed — unless you want a clean root. Your call. |

## Secrets check (must happen before any push)

A Replit scaffold frequently commits a `.env` with real keys (Supabase
URL/anon key, a session secret, a database URL). Before GitHub becomes
authoritative:
1. Grep the scaffold for committed secrets (`.env`, hardcoded keys in
   source, connection strings).
2. Any real secret found is treated as **compromised** (it was in a repo)
   → rotate it in Supabase/provider, do not just delete the file.
3. The approved `.env.example` contains **no real values** — only var
   names and instructions.

I can't run this grep against your repo from here; it's the first step
of execution once the plan is approved, and its results may add items to
the REMOVE list.

## What execution looks like (after approval)

1. Run the secrets audit; report findings.
2. Reconcile the actual repo contents against the REMOVE/KEEP/REVIEW
   tables; surface anything unclassified before touching it.
3. Remove REMOVE-list scaffold files.
4. Merge KEEP-list infrastructure (`.gitignore`) rather than overwrite.
5. Lay down the approved Milestone 2 implementation (Phase 2).
6. Full pre-commit audit (no secrets / placeholders / TODOs / scaffold /
   unused files).
7. Produce all Phase-2 deliverables, commit as the foundation.

## What I will NOT do without a further explicit go-ahead

- Delete anything before this plan is approved.
- Rewrite or squash existing git history (a REVIEW item, your decision).
- Begin Milestone 3 — the approval gate stands.
Nothing has been deleted. Awaiting review of this plan before executing Phase 1.
