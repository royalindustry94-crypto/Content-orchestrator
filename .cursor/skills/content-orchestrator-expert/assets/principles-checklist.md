# Principles checklist (quick)

- [ ] Multi-tenancy preserved
- [ ] Workspace isolation (`workspace_id` + RLS story) intact
- [ ] Human Review Gate not bypassable by design
- [ ] Spend controls still enforced before costly work
- [ ] Provider specifics at adapter/worker edge
- [ ] Audit trail for sensitive transitions
- [ ] No TODO / placeholder / silent failure on shipped paths
- [ ] Docs + tests + migration strategy considered
- [ ] No unjustified Executive Hub coupling
- [ ] No duplicate orchestration SoT

Any unchecked FAIL → escalate before ALIGN/VERIFIED.
