# Risk Register — Content Orchestrator

**Purpose:** Identify material risks for a bootstrapped, multi-tenant content orchestration SaaS and define mitigations.  
**Review cadence:** Monthly; immediately after any Sev-1.

**Severity scale:** Critical / High / Medium / Low  
**Likelihood:** High / Medium / Low (qualitative)

---

## 1. Technical

| ID | Risk | Sev | Likely | Mitigation |
|----|------|-----|--------|------------|
| T1 | Cross-tenant data exposure (RLS bypass, bug, misconfig) | Critical | Med | FORCE RLS; automated tenancy tests; security reviewer agent; no raw SQL without workspace constraint; incident runbook; pentest when revenue allows |
| T2 | Review Gate bypass (publish without approval) | Critical | Med | Gate as server-side invariant; tests forbid client-only enforcement; audit log on state transitions |
| T3 | Spend controls fail (runaway provider charges) | Critical | Med | Pre-flight estimates; hard stop in worker before provider call; anomaly alerts; default low caps; prefer BYOK |
| T4 | Worker / queue backlog destroys TTV | High | Med | Simple architecture; concurrency limits per tenant; backpressure; visible job status |
| T5 | Provider API breaking changes / quality cliffs | High | High | Abstract providers; multi-provider option later; communicate quality as BYOK-variable; don’t brand as “best generator” |
| T6 | Schema migration outage | High | Med | Expand/contract migrations; replay tests in CI; backup/restore drills |
| T7 | Secret leakage (API keys, BYOK keys) | Critical | Med | KMS/envelope encryption patterns; never log secrets; Gitleaks; rotate runbooks |

---

## 2. Financial

| ID | Risk | Sev | Likely | Mitigation |
|----|------|-----|--------|------------|
| F1 | Negative margin on platform-metered AI/video | Critical | Med | BYOK-first; strict markup; kill free unlimited gen; monitor cost per video weekly |
| F2 | CAC exceeds LTV (paid ads too early) | High | High if ads early | Defer ads; organic + outbound; measure activation first |
| F3 | Support costs from Starter-heavy mix | High | Med | Limits on Starter; docs; nudge to Pro; don’t overserve anti-ICP |
| F4 | Founder runway exhaustion before PMF | Critical | Med | Keep infra minimal; contractor discipline; design-partner revenue early; avoid vanity spend |
| F5 | Refund / chargeback abuse on trials | Med | Med | Hard caps; card verification when needed; Gate reduces “wrong publish” disputes but not cost disputes |

---

## 3. Legal

| ID | Risk | Sev | Likely | Mitigation |
|----|------|-----|--------|------------|
| L1 | Customer content rights / copyright claims | High | Med | ToS: customer owns inputs/outputs as applicable; customer responsible for rights; take-down process |
| L2 | Training / provider data use ambiguity | High | Med | Prefer providers with clear no-train options; disclose subprocessors; BYOK shifts some risk |
| L3 | Defamation / harmful generated content published | High | Med | **Mandatory Review Gate**; customer is publisher of record; audit trails |
| L4 | Contract overpromise (uptime, quality SLAs) | Med | Med | Conservative SLAs; no unlimited liability; Enterprise legal review |

---

## 4. Platform (dependency)

| ID | Risk | Sev | Likely | Mitigation |
|----|------|-----|--------|------------|
| P1 | OpenAI/Anthropic/video APIs price hike or rate limit | High | High | BYOK; multi-provider; spend caps; cache where safe |
| P2 | Stripe outage / account review | High | Low–Med | Status comms; manual invoice fallback for Agency |
| P3 | Cloud host regional failure | High | Low | Backups; RPO/RTO documented; single-region OK early with honest status page |
| P4 | OAuth provider policy changes | Med | Med | Email login fallback |

---

## 5. Compliance

| ID | Risk | Sev | Likely | Mitigation |
|----|------|-----|--------|------------|
| C1 | GDPR / privacy requests | High | Med | Data export/delete paths; DPA template; minimize PII; subprocessors list |
| C2 | SOC 2 pressure from Enterprise before ready | Med | Med | Don’t claim SOC 2 until earned; sell Agency on isolation + audits first; roadmap SSO/DPA in Q4 |
| C3 | Storing BYOK credentials = high trust bar | High | High | Encryption, access control, customer-managed revoke; document practices honestly |
| C4 | Marketing claims that imply guaranteed compliance | Med | Med | Legal review of site copy; no “bank-grade” fluff |

---

## 6. Competitive

| ID | Risk | Sev | Likely | Mitigation |
|----|------|-----|--------|------------|
| K1 | Make/Zapier templates close the “content stack” gap | High | Med | Go deeper on Gate, spend ledger, brand/workspace UX — not connector parity |
| K2 | Relay.app or HITL tools add content features | Med | Med | Stay vertical; ship templates + video cost controls faster in-domain |
| K3 | Race to free autonomous agents | High | High | Refuse to compete on autonomy theater; own “safe orchestration” niche |
| K4 | Price war with horizontal tools | Med | Med | Value-based packaging; don’t match free tiers feature-for-feature |

---

## 7. Operational

| ID | Risk | Sev | Likely | Mitigation |
|----|------|-----|--------|------------|
| O1 | Founder bus factor = 1 | Critical | High | Docs, runbooks, `AGENTS.md`/rules, simple stack; contractor backup for ops |
| O2 | On-call burnout from worker failures | High | Med | Aggressive alerting hygiene; provider status; queue limits; paid plans fund headroom |
| O3 | Design partners dominating roadmap into custom one-offs | High | High | Written ICP; score features by multi-customer demand; preserve invariants |
| O4 | Channel bans (Reddit/spam accusations) | Med | Med | Value-first participation; separate launch posts carefully |
| O5 | Brand damage from customer misuse despite Gate | Med | Med | Gate + ToS; educate; refuse customers seeking bypass |

---

## 8. Top risks (executive view)

1. **Tenant isolation failure** (company-ending)  
2. **Spend control failure** (margin + trust)  
3. **Gate bypass** (positioning collapse + legal)  
4. **Runway / negative AI margins**  
5. **Wrong ICP / autonomy-chasing messaging**  

---

## 9. Risk response policy

- **Critical:** Immediate owner, public status if customer-impacting, feature freeze if trust-related  
- **High:** Mitigate within current quarter roadmap  
- **Medium/Low:** Track; accept or schedule  

**Never acceptable residual risk:** intentional Gate disable flags, shared-tenant “shortcut” for speed, unlimited free generation.

---

## 10. Assumptions

- Primary market has standard SaaS ToS enforceability  
- Customers accept they are responsible for final publish decisions (Gate reinforces this)  
- Bootstrapped ops means some Medium risks are **accepted** temporarily with monitoring — not ignored  

---

*Update this register when providers, pricing, or markets change.*
