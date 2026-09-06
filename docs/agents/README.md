# Specialized agent roster

**Product:** Content Orchestrator / The Business Manager  
**Owner:** Founder  
**Status:** Active operating model — auditor is live; continuation is dormant until Founder takeover

This repository now has two Founder-controlled specialist roles. They are not a
substitute for `AGENTS.md`, `docs/MILESTONE_AUDIT_STANDARD.md`, or the
Human Review Gate. They exist so ChatGPT/Codex work can be independently
audited, and so a second builder can continue the product when ChatGPT is
unavailable.

| Role | Activation | May change product code? | May certify its own work? |
|---|---|---|---|
| **ChatGPT Independent Auditor** | Always available. Use for every ChatGPT/Codex/Copilot-attributed change. | No, except audit reports and evidence docs | No. Never the sole certifier of work it implemented. |
| **Build Continuation Agent** | **Dormant.** Activates only on an explicit Founder takeover phrase. | Yes, after takeover, on the highest-value authorized item | No. The auditor (or another independent pass) must certify. |

## Live chat screens

These are separate Cursor Cloud Agent chats. Open the one you want to talk to.
Do not mix roles in this setup chat.

| Role | Chat screen |
|---|---|
| ChatGPT Independent Auditor | https://cursor.com/agents/bc-fbcc19be-ddb7-544d-8561-a0988ae4e7bb |
| Build Continuation Agent (dormant) | https://cursor.com/agents/bc-e13d6abd-bd20-57a9-afb6-4c9e391089b4 |

Send audit targets only in the Auditor chat. Send `TAKEOVER` only in the
Continuation chat.

To recreate a screen later, copy the matching prompt from
[`LAUNCH_PROMPTS.md`](LAUNCH_PROMPTS.md) into a new Cursor Cloud Agent, or
select the matching custom agent:

- GitHub Copilot / VS Code: `.github/agents/*.agent.md`
- Cursor: `.cursor/agents/*.md`

## Required reading order for either agent

1. `AGENTS.md`
2. `docs/MILESTONE_AUDIT_STANDARD.md`
3. `docs/agents/BUILD_TO_LIVE_PROCESS.md`
4. The role playbook (`CHATGPT_INDEPENDENT_AUDITOR.md` or `BUILD_CONTINUATION_AGENT.md`)
5. `docs/agents/HANDOFF_PROTOCOL.md`
6. Current `docs/LAUNCH_BLOCKERS.md` and the exact candidate SHA

## What these agents are not

- Not a license to merge draft PRs marked do-not-merge
- Not a license to enable live providers, billing, or external publishing
- Not a replacement for Founder approval on release, deploy, or gate overrides
- Not the unfinished Copilot six-profile bootstrap in issue #52 / PR #53

## Current ChatGPT / Codex work under audit

Treat these as ChatGPT-family builder artifacts unless the Founder says otherwise:

- Codex / ChatGPT lanes: PRs #79, #82 and issues #76, #75
- Copilot assurance/audit lanes the Founder asks to include: PRs #83, #84, #74
- Historical builders already on `main`: Manus / Lumora automation commits that landed the preview pipeline via PR #48

Baseline audit: [`audits/CHATGPT_WORK_BASELINE_AUDIT_2026-09-06.md`](audits/CHATGPT_WORK_BASELINE_AUDIT_2026-09-06.md)
