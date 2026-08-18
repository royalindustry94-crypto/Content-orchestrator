# Platform Policy Control Matrix

**Status:** Repository policy and operating-control specification.
**Implementation state:** **PARTIALLY CLOSED.** Lumora’s Human Review Gate (HRG) is a verified workflow control, but this candidate does **not** implement automated rights verification, AI-disclosure classification, or platform-policy adjudication. No statement in this document should be read as proof that a platform will accept or monetize any output.

> **Non-negotiable rule:** A platform destination may not be published automatically to work around a failed, missing, stale, or cross-workspace review decision. The HRG authorizes a specific content version and action; platform-policy flags remain a blocking review input.

## Control matrix

| Platform | Policy-risk trigger | Required pre-publication evidence | HRG criteria | Publication-blocking condition | Post-publication monitoring and incident action |
|---|---|---|---|---|---|
| YouTube | Content is generic, repetitive, mass-produced, reused without meaningful transformation, or designed to manipulate engagement. YouTube describes these patterns as ineligible for monetization and prohibits automated/synthetic mass production.[1][2] | Content/version ID; provenance record for script, visual, audio, music, and third-party assets; human statement of original/transformative value; duplicate-similarity review; title/thumbnail/description review. | Reviewer confirms meaningful creator contribution, accurate metadata, no scraped or duplicated asset use, and no deceptive engagement tactic. | Missing rights/provenance; material similarity to previously scheduled/published content; unreviewed template batch; manipulative metadata; HRG not approved for this version. | Track removal, strike, demonetization, Content ID/rights claim, and viewer complaint. Immediately pause related scheduled jobs; preserve immutable evidence; open a corrective review; do not re-upload a cosmetically modified copy. |
| YouTube | A realistic person, event, place, or scene was meaningfully generated or altered by AI. YouTube requires disclosure for this class of content.[3] | Reviewer-visible disclosure decision, the reason, and required upload attribute value. | Reviewer confirms the upload configuration declares AI use when required and that the final rendered version matches the reviewed asset. | Disclosure required but unavailable, declined, or unverifiable; any version change after the disclosure decision. | Record platform label state and adverse action; pause related workflows if label omission or misleading presentation is reported. |
| TikTok | Realistic AI-generated/significantly edited content is unlabeled, a likeness is used without authority, or synthetic content can harmfully mislead. TikTok requires labels for realistic AIGC and prohibits defined harmful uses even when labelled.[4][5] | Version-specific AIGC determination; source/consent record for real-person likenesses; platform label setting; factual-risk and public-importance assessment. | Reviewer confirms label is selected where required, no forbidden likeness/authority/crisis depiction is present, and claims are supportable. | Required label absent; unverified public-importance claim; no consent/right for a depicted private person; prohibited under-18 likeness; insufficient reviewer evidence. | Monitor removal, restriction, FYF ineligibility, warnings, and reports. Pause related destinations, preserve original/version, assess user harm, and escalate materially misleading content immediately. |
| TikTok | Unoriginal/reused material, IP infringement, fake engagement, or automation intended to bypass platform systems. TikTok prohibits these practices and may restrict or ban accounts.[5][6] | Asset-rights register; content originality review; publication cadence and destination log; no fake engagement/automation declaration. | Reviewer confirms the content is created or licensed for use and the publishing action is ordinary platform API use rather than manipulation. | Rights record absent; duplicate/reused output without new value; engagement manipulation instruction; any attempt to bypass a platform control. | Retain platform notices, stop the affected workflow, investigate account-wide pattern risk, and require a human release decision before resuming. |
| Instagram | Content infringes copyright or trademark, or has no documented right to use. Instagram terms prohibit IP-infringing content.[7] | Asset provenance, license/consent identifiers, trademark/reference review, and reviewed final caption/media package. | Reviewer confirms rights evidence is adequate for all externally sourced assets and captions do not imply false affiliation. | Unknown asset source or license; unresolved claim; use of protected brand/personality without a documented basis. | Record takedown/claim; disable related publication jobs and investigate all outputs sharing the asset or template. |
| Instagram | Digitally created/altered photorealistic video or realistic-sounding audio needs transparency, or the content creates a material deception risk. Meta describes disclosure/label expectations and potential penalties for non-disclosure.[8] | AI-use determination; disclosure configuration; final render hash/version; any C2PA or source metadata retained when available. | Reviewer confirms the disclosure decision and final asset match. | Required disclosure unavailable; final render changed; plausible material deception risk. | Preserve label state and platform notice; pause replication/scheduling and conduct a policy review. |
| Instagram | Spam or unwanted commercial/harassing communications. Instagram guidelines prohibit spam.[9] | Destination/account rate record, audience-targeting rationale, content-deduplication result, and approved action. | Reviewer confirms cadence and copy are not bulk/repetitive spam and any commercial disclosure required by the user’s jurisdiction/platform setup is addressed. | Rate/cadence exceeds workspace policy; duplicate copy without substantive change; missing approval; distribution intended to manipulate engagement. | Monitor reach anomalies, restrictions, removals, and complaints; stop queued jobs and investigate cross-workspace or repeated-template use. |

## Common policy-control workflow

| Stage | Required control | Evidence retained | Automation boundary |
|---|---|---|---|
| Generate | Assign immutable content/version ID; capture provider, input, asset, and cost lineage. | Version, asset lineage, source/rights fields, provider-effect/audit records where supported. | Generation may be automated only within approved spend and workspace controls. |
| Preflight | Calculate duplicate/template signals; collect destination metadata; flag AI, rights, factual, sensitive-topic, and cadence risks. | Preflight result, unresolved flags, policy matrix version. | Flags are advisory until a rule is implemented and validated; they are not a substitute for human policy judgment. |
| Review | Bind reviewer identity, decision, timestamp, reasons, exact content version, and exact publish/schedule action. | HRG decision/audit record. | No scheduler, retry, worker, or direct API path may substitute or resurrect a decision. |
| Publish | Validate that the reviewed version and allowed destination/action match the HRG decision, the policy preflight, and spend authorization. | Provider request/response identifier, time, destination, selected disclosure settings. | If any validation is missing, fail closed and retain the job for review—not auto-publish. |
| Monitor | Ingest platform response, rights claims, moderation events, and performance/complaint signals. | Event/audit log and incident record. | Monitoring may alert; it may pause matching jobs. It may not silently republish or override a reviewer. |
| Incident | Triage severity, pause relevant schedules, preserve immutable evidence, notify the workspace owner, and decide correction/takedown through HRG. | Incident timeline, affected versions/destinations, decision and remediation. | High-risk legal, safety, impersonation, or public-interest cases require human escalation. |

## Required implementation backlog

The following are **not implemented or verified by this candidate** and remain required before any claim of automated platform compliance:

| Gap | Status | Required next implementation / evidence |
|---|---|---|
| Versioned policy preflight record | CONFIRMED OPEN | Persist destination-specific preflight results and bind them to the HRG decision and final publish action. |
| Rights / provenance verification | CONFIRMED OPEN | Add asset-rights fields, evidence attachment, and reviewer blocking rules; do not claim legal clearance from a text field alone. |
| Disclosure configuration verification | CONFIRMED OPEN | Store the destination disclosure setting and reconcile it against provider response before delivery. |
| Duplicate / repetitive-content guardrail | CONFIRMED OPEN | Define similarity thresholds and human override audit; validate with adversarial tests so a batch cannot evade review by superficial edits. |
| Post-publication incident intake | CONFIRMED OPEN | Implement destination event ingestion, workspace notifications, pause controls, and an immutable incident ledger. |

## References

[1]: https://support.google.com/youtube/answer/1311392?hl=en
[2]: https://support.google.com/youtube/answer/2801973?hl=en
[3]: https://support.google.com/youtube/answer/14328491?hl=en
[4]: https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content
[5]: https://www.tiktok.com/safety/en/policies-and-engagement/integrity-authenticity
[6]: https://support.tiktok.com/en/safety-hc/account-and-user-safety/intellectual-property
[7]: https://help.instagram.com/535503073130320/
[8]: https://about.fb.com/news/2024/02/labeling-ai-generated-images-on-facebook-instagram-and-threads/
[9]: https://about.instagram.com/blog/announcements/instagram-community-guidelines-faqs
