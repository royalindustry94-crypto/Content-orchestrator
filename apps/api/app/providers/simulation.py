"""Deterministic, offline, zero-cost provider for pre-vendor testing.

This provider exists so the Scout → Strategist → Content → Producer →
Compliance chain can be exercised end to end before any paid vendor is
activated. It performs no network I/O, spends nothing, and derives every field
from a hash of its own request, so the same request always produces the same
output and a repeated request is correctly detected as a duplicate downstream.

Nothing here weakens a control. Output is labelled ``simulation`` in every
record the services persist, the independent auditors still run against it for
real, the Human Review Gate is still mandatory, and external publishing stays
disabled. Sources cite the reserved ``.invalid`` TLD precisely so simulated
evidence can never be mistaken for a real citation.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal

from app.providers.base import (
    SIMULATION,
    ComplianceRequest,
    ComplianceResult,
    ContentRequest,
    ContentResult,
    CreativeDirectionDraft,
    OpportunityDraft,
    ProductionRequest,
    ProductionResult,
    ProviderUsage,
    RenderedAssetDraft,
    ResearchRequest,
    ResearchResult,
    ScriptDraft,
    SourceDraft,
    StrategyBriefDraft,
    StrategyRequest,
    StrategyResult,
)

# Simulated evidence must never resolve. `.invalid` is reserved by RFC 2606 for
# exactly this purpose, so a reader (or a future crawler) cannot mistake one of
# these citations for a real publication.
SOURCE_HOST = "simulated-source.invalid"

# The Writer must reproduce this phrase verbatim and the brand auditor checks
# for it, so the two are defined once here rather than kept in sync by hand.
REQUIRED_PHRASE = "outcomes track how much preparation happened"

_ANGLES = (
    "a practitioner walkthrough grounded in the collected evidence",
    "a myth-versus-evidence comparison drawn from the collected sources",
    "a short decision guide assembled from the collected evidence",
    "a before-and-after teardown supported by the collected sources",
)

_AUDIENCES = (
    "operators evaluating the topic for the first time",
    "practitioners who already tried the obvious approach",
    "team leads deciding whether to invest further",
    "specialists comparing competing approaches",
)

_TONES = ("clear", "measured", "direct", "considered")
_PACINGS = ("measured", "brisk", "even", "deliberate")
_STRUCTURES = (
    "problem-evidence-action",
    "question-evidence-answer",
    "claim-evidence-caveat",
    "context-evidence-next-step",
)
_PUBLISHERS = (
    "Simulated Field Notes",
    "Simulated Practitioner Review",
    "Simulated Industry Digest",
)
_AUTHORS = ("A. Simulated", "B. Simulated", "C. Simulated")
_FORMATS = ("short_form_video", "short_form_media", "explainer_clip")
_PLATFORMS = ("youtube_shorts", "tiktok", "instagram_reels")


def _digest(*parts: str) -> str:
    return hashlib.sha256("\u001f".join(parts).encode("utf-8")).hexdigest()


def _pick(bank: tuple[str, ...], seed: str, salt: str) -> str:
    """Stable selection from a phrase bank, keyed by the request itself."""
    index = int(_digest(seed, salt)[:8], 16) % len(bank)
    return bank[index]


def _slug(value: str, *, limit: int = 48) -> str:
    cleaned = [char.lower() if char.isalnum() else "-" for char in value.strip()]
    slug = "".join(cleaned).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return (slug[:limit].strip("-")) or "topic"


def _headline(value: str) -> str:
    """First clause of the objective, capitalised, for use in prose."""
    head = value.strip().split(".")[0].strip()
    if not head:
        head = "the requested subject"
    return head[:160]


class SimulationPipelineProvider:
    """Offline provider that produces auditable, obviously-simulated output.

    The generated prose deliberately avoids numerals, superlatives, and
    forward-looking promises. Those are the exact patterns the Content
    Department's fact and language auditors flag, and a provider that tripped
    its own downstream auditors would make the audit gates untestable.
    """

    name = SIMULATION
    state_label = SIMULATION
    is_configured = True

    # --- Research (Scout) ---------------------------------------------------

    async def research(self, request: ResearchRequest) -> ResearchResult:
        seed = _digest(str(request.workspace_id), request.objective)
        topic = _headline(request.objective)
        slug = _slug(topic)
        angle = _pick(_ANGLES, seed, "angle")
        audience = _pick(_AUDIENCES, seed, "audience")
        platform = _pick(_PLATFORMS, seed, "platform")
        content_format = _pick(_FORMATS, seed, "format")

        # Three independent sources: the Research Auditor warns when only a
        # single accepted source supports an opportunity, and blocks on
        # duplicate content digests, so each excerpt is distinct.
        aspects = (
            (
                "practitioner-report",
                "what practitioners reported after trying the approach",
                "Practitioners reported that the approach held up once they had "
                "accounted for setup effort.",
            ),
            (
                "method-review",
                "how the method is described by the people who maintain it",
                "The maintainers describe the method as dependent on preparation "
                "rather than on tooling.",
            ),
            (
                "counter-evidence",
                "where the approach did not hold and why",
                "Several accounts describe cases where the approach did not hold, "
                "mostly traced back to skipped preparation.",
            ),
        )
        sources = [
            SourceDraft(
                canonical_url=f"https://{kind}.{SOURCE_HOST}/{slug}",
                source_type="simulated_reference",
                publisher=_pick(_PUBLISHERS, seed, kind),
                author=_pick(_AUTHORS, seed, f"author-{kind}"),
                claim_supported=claim,
                freshness="fresh",
                confidence=Decimal("0.62"),
                excerpt=(
                    f"SIMULATED SOURCE — no real publication backs this text. "
                    f"On {topic}: {excerpt}"
                ),
            )
            for kind, claim, excerpt in aspects
        ]

        opportunity = OpportunityDraft(
            title=f"{topic} — evidence-led explainer",
            topic=topic,
            summary=(
                f"SIMULATED FINDING. Collected references about {topic} agree that outcomes "
                "depend on preparation rather than on tooling, and they disagree about how "
                "much setup effort is worth it. That disagreement is the opening for a short, "
                "evidence-led explainer."
            ),
            proposed_angle=angle,
            target_audience=audience,
            target_platform=platform,
            suggested_format=content_format,
            freshness="fresh",
            confidence=Decimal("0.62"),
            risk="low",
            component_scores={
                "evidence_support": 0.62,
                "audience_fit": 0.58,
                "differentiation": 0.55,
            },
            score_reasoning={
                "evidence_support": "Three simulated references agree on the core claim.",
                "audience_fit": "The audience is addressable on short-form platforms.",
                "differentiation": "The disagreement between sources is not widely covered.",
            },
        )
        return ResearchResult(
            sources=sources,
            opportunity=opportunity,
            usage=ProviderUsage(provider=SIMULATION),
        )

    # --- Strategy -----------------------------------------------------------

    async def strategy(self, request: StrategyRequest) -> StrategyResult:
        seed = _digest(str(request.workspace_id), request.objective, *request.opportunity_topics)
        topic = _headline(
            request.opportunity_topics[0] if request.opportunity_topics else request.objective
        )
        angle = (
            request.opportunity_angles[0]
            if request.opportunity_angles
            else _pick(_ANGLES, seed, "angle")
        )
        evidence = (
            request.opportunity_summaries[0]
            if request.opportunity_summaries
            else f"Simulated references about {topic}."
        )
        platform = request.target_platform or _pick(_PLATFORMS, seed, "platform")
        brief = StrategyBriefDraft(
            objective=_headline(request.objective),
            target_audience=_pick(_AUDIENCES, seed, "audience"),
            target_platform=platform,
            content_format=_pick(_FORMATS, seed, "format"),
            creative_angle=angle,
            core_message=(
                f"On {topic}, preparation decides the outcome far more than tooling does."
            ),
            hook_direction="Open on the disagreement between the collected sources.",
            cta_direction="Invite the viewer to check the cited evidence before acting.",
            business_goal="Establish credibility with an addressable short-form audience.",
            success_metric="Qualified replies from the target audience.",
            commercial_goal="Support the top of the advisory funnel.",
            evidence_summary=(
                f"SIMULATED EVIDENCE SUMMARY. {evidence}"
            ),
            reasoning=(
                "The simulated references agree on the core claim and disagree on effort, "
                "so an explainer that names the disagreement is defensible without "
                "overstating any outcome."
            ),
            confidence=Decimal("0.60"),
            priority="medium_priority",
            estimated_complexity="low",
            risk_level="low",
            recommended_length="under one minute",
            recommended_posting_window="weekday mornings, audience local time",
            required_assets=["narration", "captions"],
            production_requirements=["vertical framing", "burned-in captions"],
            rights_requirements=["synthetic narration only", "no third-party footage"],
            compliance_requirements=["disclose synthetic media", "no performance promises"],
            component_scores={"evidence": 0.6, "feasibility": 0.7, "commercial_fit": 0.55},
            score_reasoning={
                "evidence": "Traceable to audited simulated opportunities.",
                "feasibility": "Single narrator format with no third-party footage.",
                "commercial_fit": "Matches the advisory funnel.",
            },
            estimated_provider_usage={"narration": 1, "render": 1},
            estimated_cost_range={"low_usd": "0.00", "high_usd": "0.00"},
        )
        return StrategyResult(brief=brief, usage=ProviderUsage(provider=SIMULATION))

    # --- Content Department -------------------------------------------------

    async def content(self, request: ContentRequest) -> ContentResult:
        seed = _digest(str(request.workspace_id), request.objective)
        topic = _headline(request.objective)
        concept = request.creative_angle or _pick(_ANGLES, seed, "angle")
        message = request.core_message or (
            f"On {topic}, preparation decides the outcome far more than tooling does."
        )
        direction = CreativeDirectionDraft(
            creative_concept=(
                f"A single narrator walks through {topic} using only the cited simulated "
                f"evidence, framed as {concept}."
            ),
            opening_pattern=request.hook_direction
            or "Open on the disagreement between the collected sources.",
            story_structure=_pick(_STRUCTURES, seed, "structure"),
            tone=_pick(_TONES, seed, "tone"),
            pacing=_pick(_PACINGS, seed, "pacing"),
            visual_direction="Evidence-led captions over a plain background.",
            audio_direction="Clear synthetic narration, no music bed.",
            desired_emotion="confidence",
            production_complexity="low",
            estimated_duration=request.recommended_length or "under one minute",
            # Both lists are literal phrases so the brand auditor can check
            # them by inspection rather than by interpretation.
            required_claims=[REQUIRED_PHRASE],
            prohibited_claims=[
                "guaranteed",
                "go viral",
                "increase revenue by",
                "best in the world",
                "risk-free",
            ],
            required_assets=["narration", "captions"],
            risk_notes=[
                "Simulated provider output; the cited evidence is synthetic.",
                f"Core message to preserve in any revision: {message}",
            ],
        )

        # The script avoids numerals and superlatives on purpose: those are the
        # patterns the fact and language auditors treat as source-requiring
        # claims, and simulated evidence cannot substantiate them.
        script = ScriptDraft(
            title=f"{topic}: what the evidence actually says",
            description=(
                f"SIMULATED DRAFT. An evidence-led short explainer about {topic}, "
                "produced by the simulation provider for pipeline testing."
            ),
            hook=(
                f"Everyone seems to disagree about {topic} — so let us look at what the "
                "collected sources actually say."
            ),
            body=(
                f"SIMULATED SCRIPT — generated offline for pipeline testing, not for publication. "
                f"The sources gathered on {topic} agree on one point: {REQUIRED_PHRASE} "
                "before anyone touched a tool. Where they part company is "
                "on how much of that preparation is worth doing. One account describes teams "
                "who front-loaded the setup and found the approach held. Another describes the "
                "same approach falling over, and traces it back to preparation that got skipped. "
                "Neither account promises a particular result, and neither should you. "
                f"So if you are weighing {topic}, the useful question is not whether the "
                "approach works, but whether you are ready to do the preparation it assumes."
            ),
            cta=(
                "Check the cited evidence yourself before you act on any of this, and treat "
                "anything unsourced as an open question."
            ),
        )
        return ContentResult(
            direction=direction, script=script, usage=ProviderUsage(provider=SIMULATION)
        )

    # --- Production (Producer) ----------------------------------------------

    async def production(self, request: ProductionRequest) -> ProductionResult:
        platform = request.target_platform or "youtube_shorts"
        duration = Decimal(str(request.target_duration_seconds or 45))
        # The hash binds the artifact to the exact script it was rendered from,
        # which is what Media QA and Compliance later re-verify.
        artifact_hash = _digest(
            SIMULATION,
            platform,
            request.script_hook,
            request.script_body,
            request.script_cta,
        )
        assets = [
            RenderedAssetDraft(
                asset_type="voiceover",
                model_version="simulation-narration-v1",
                duration_seconds=duration,
                dimensions={},
                generation_settings={"voice": "simulated-neutral", "language": "en"},
                cost_usd=Decimal("0.00"),
            ),
            RenderedAssetDraft(
                asset_type="subtitle",
                model_version="simulation-captions-v1",
                duration_seconds=duration,
                dimensions={},
                generation_settings={"format": "burned_in", "language": "en"},
                cost_usd=Decimal("0.00"),
            ),
            RenderedAssetDraft(
                asset_type="video",
                model_version="simulation-render-v1",
                duration_seconds=duration,
                dimensions={"width": 1080, "height": 1920},
                generation_settings={"template": "evidence-captions", "fps": "30"},
                cost_usd=Decimal("0.00"),
            ),
        ]
        return ProductionResult(
            assets=assets,
            artifact_hash=artifact_hash,
            storage_reference={
                "mode": SIMULATION,
                "non_public": True,
                "detail": (
                    "No media file is produced; the simulation provider "
                    "renders metadata only."
                ),
            },
            duration_seconds=duration,
            resolution={"width": 1080, "height": 1920},
            aspect_ratio="9:16",
            container="mp4",
            codec="h264",
            usage=ProviderUsage(provider=SIMULATION),
        )

    # --- Compliance ---------------------------------------------------------

    async def compliance(self, request: ComplianceRequest) -> ComplianceResult:
        return ComplianceResult(
            risk_level="low",
            reused_content_risk="low",
            monetization_risk="low",
            rights_status="verified",
            rights_basis=(
                "Fully synthetic narration, captions, and render produced by the simulation "
                "provider; no third-party material is incorporated."
            ),
            findings=[],
            evidence=[
                {
                    "check": "synthetic_origin",
                    "result": "every component was generated offline by the simulation provider",
                },
                {
                    "check": "artifact_binding",
                    "result": f"assessment is bound to artifact hash {request.artifact_hash}",
                },
            ],
            required_disclosures=["This content contains synthetic media."],
            policy_version="simulation-policy-v1",
            usage=ProviderUsage(provider=SIMULATION),
        )
