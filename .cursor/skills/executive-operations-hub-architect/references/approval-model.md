# Approval model — Hub vs product

## Two approval planes (do not merge)

| Plane | What it approves | Owner |
|-------|------------------|-------|
| **Product Human Review Gate** | Tenant content / workflow advances that require human review | Content Orchestrator product (`/content-orchestrator-expert`, Backend) |
| **Ops Hub approvals** | Engineering/ops actions: release window, agent spend policy, exceptional merge signals, change management | Executive Operations Hub |

## Rules

1. Hub automation may **queue, notify, and track** product review items — it must not **auto-approve** product Review Gate decisions unless `/ceo` explicitly designs a separate product feature with Architect+Security review.
2. Spend controls for **tenant provider spend** remain in product; Hub may track **agent/infra cost** separately without bypassing product caps.
3. Reduce manual coordination (routing, status, reminders) aggressively; reduce required human judgment gates only with explicit CEO approval.

## Example Hub approval flow

```text
Change proposed → Hub task → Agent/engineer work → CI green
  → Ops checklist (QA/Security/Release evidence attached)
  → Ops approver (if required) → Human merge order
```

Product content still flows through Review Gate inside the product.
