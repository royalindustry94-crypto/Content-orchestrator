# Three-lane agent workspace

**Product:** The Business Manager

**Integration inputs:** PR #71 at `dcb4b6e7746e330265e362dc8b59f7ae288932c1`
and PR #72 at `f151d7edb0e8b1df7e7fe2a21d9a526e1f765a6e`

**Release state:** development-only; exact-head CI and independent audit pending

This file divides the next milestone into three disjoint writing lanes. GitHub
issues, branches, commits and structured handoffs are the communication
channel. Chat statements are not release evidence.

## Shared rules

- Read `AGENTS.md`, the closest directory `AGENTS.md`, and the named skills
  before editing.
- One agent owns one branch. Do not push to another lane's branch.
- Rebase or merge only through the integration coordinator.
- No agent may merge, deploy, access production data, enable billing/providers,
  or enable external publishing.
- Human Review, FORCE RLS and spend fail-closed behavior are immutable.
- Generated audit reports are verified PDFs uploaded as artifacts and are
  never committed to Git.
- Every handoff names the exact branch, head SHA, base SHA, migration head,
  dirty state, checks and unresolved findings.

## Lane 1 - Codex: Human-Finished Creative Core

**Branch:** `codex/human-finished-creative-core`

**Task:** provider-neutral backend for importing externally created media,
immutable revisions and exact-artifact human approval.

Owned paths:

- `apps/api/app/models/`
- `apps/api/app/schemas/`
- `apps/api/app/services/`
- `apps/api/app/api/routes/`
- `apps/api/alembic/versions/`
- `apps/api/tests/`
- matching backend work-package documentation

Required project skills:

- `.agents/skills/milestone-plan/SKILL.md`
- `.agents/skills/safe-migration/SKILL.md`
- `.agents/skills/agent-handoff/SKILL.md`
- `.agents/skills/release-gate/SKILL.md`

Reference repositories, not approved dependencies:

- `tus/tus-resumable-upload-protocol` - upload semantics
- `tus/tus-js-client` - resumable client behavior
- `boto/boto3` - S3-compatible server-side storage patterns

Acceptance boundary: no media blob in PostgreSQL; same-workspace database
constraints and FORCE RLS; originals never overwritten; file validation;
approval invalidates on hash/version change; complete negative authorization
tests. Storage provider activation remains out of scope.

## Lane 2 - Cursor: Human Creative Workspace

**Branch:** `cursor/human-creative-workspace`

**Task:** mobile-first interface for human custom work, uploads, revision notes,
before/after comparison, request changes and final approval.

Owned paths:

- `apps/web/src/`
- `apps/web/index.html`
- web tests
- matching UI work-package documentation

Required project guidance:

- `.cursor/rules/content-orchestrator.mdc`
- `.cursor/rules/web-quality.mdc`
- `.agents/skills/browser-smoke/SKILL.md`
- `.agents/skills/agent-handoff/SKILL.md`

Reference repositories, not approved dependencies:

- `transloadit/uppy` - accessible upload UX patterns
- `tus/tus-js-client` - resumable upload client behavior
- `w3c/aria-practices` - dialog, progress and keyboard interaction patterns

Acceptance boundary: existing API contracts or an agreed contract fixture;
desktop and 390px mobile; keyboard and screen-reader labels; no embedded API
keys; no local fake success; external publishing remains disabled. Cursor does
not create migrations or alter backend authorization.

## Lane 3 - Copilot: Daily Assurance Worker

**Branch:** `copilot/daily-assurance-worker`

**Task:** scheduled and manual repository audit with PDF artifacts and a strict
allowlist for low-risk repair branches.

Owned paths:

- `.github/workflows/daily-assurance.yml`
- `.github/agents/daily-assurance-worker.agent.md`
- `scripts/daily_assurance/`
- assurance-only tests and operations documentation

Required project skills:

- `.agents/skills/milestone-audit/SKILL.md`
- `.agents/skills/release-gate/SKILL.md`
- `.agents/skills/browser-smoke/SKILL.md`
- `.agents/skills/agent-handoff/SKILL.md`

Reference repositories, not approved dependencies:

- `github/codeql-action` - supported GitHub analysis workflow
- `gitleaks/gitleaks-action` - secret scanning workflow
- `pypa/pip-audit` - Python dependency auditing
- `aquasecurity/trivy-action` - container/filesystem vulnerability scanning

Acceptance boundary: PDF for every run; exact SHA and change baseline; one
repair attempt per finding fingerprint; draft PR only; no self-merge or deploy.
Authentication, authorization, RLS, spend, Human Review, migrations, secrets,
provider side effects and data-loss findings are report-only blockers and can
never be automatically repaired.

## Integration order

1. Each lane publishes a structured `ready_for_review` handoff.
2. Codex integrates backend contracts before Cursor replaces contract fixtures.
3. Copilot assurance remains independently mergeable and cannot certify its
   own implementation.
4. The combined candidate runs all six required checks plus an independent
   exact-head audit delivered as a PDF.
5. Only the Founder may authorize protected merge or deployment.
