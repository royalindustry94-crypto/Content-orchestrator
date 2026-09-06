# WP-GOV-002 — Specialized auditor and continuation agents

**Status:** Implemented on this branch — configuration and playbooks only  
**Priority fit:** Development governance / Founder operating model  
**Runtime impact:** None. No product, migration, provider, billing, auth, or publish change.

## Objective

Give the Founder two durable specialist roles:

1. A ChatGPT Independent Auditor that already knows the build-to-live path and
   deep-audits ChatGPT/Codex work.
2. A Build Continuation Agent that stays dormant until the Founder explicitly
   hands over ChatGPT's lane.

## Delivered

- `docs/agents/BUILD_TO_LIVE_PROCESS.md`
- `docs/agents/CHATGPT_INDEPENDENT_AUDITOR.md`
- `docs/agents/BUILD_CONTINUATION_AGENT.md`
- `docs/agents/HANDOFF_PROTOCOL.md`
- `docs/agents/LAUNCH_PROMPTS.md`
- `docs/agents/audits/CHATGPT_WORK_BASELINE_AUDIT_2026-09-06.md`
- `.github/agents/chatgpt-independent-auditor.agent.md`
- `.github/agents/build-continuation.agent.md`
- `.cursor/agents/*` and matching non-always-apply Cursor rules
- Root `AGENTS.md` pointer

## Non-goals

- Not the six Copilot autonomy profiles in issue #52 / PR #53
- Not a merge of Codex PRs #79 / #82
- Not branch-protection mutation
- Not managed Supabase remediation (issue #66)
- Not live providers, billing, or publishing

## Acceptance

- A new Cursor/Copilot agent can be launched from the copy-paste prompts
- Continuation remains dormant without an explicit takeover phrase
- Auditor playbook requires milestone-standard PASS/CONDITIONAL/FAIL
- No runtime behavior change on this branch

## Rollback

Delete the added docs, `.github/agents/*`, `.cursor/agents/*`, and the two
non-always-apply rules; revert the `AGENTS.md` section. No schema or service
rollback is required.
