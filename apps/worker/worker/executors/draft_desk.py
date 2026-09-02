"""Draft Desk stage executor — real structured generation, never empty {}."""

from __future__ import annotations


async def draft_desk_executor(assignment_context: dict) -> tuple[bool, dict | None, str]:
    """Async adapter around the shared Draft Desk generation rules.

    The API service owns the canonical generator; the worker embeds an
    equivalent implementation so it can run without importing the API
    package. Keep outputs aligned with apps/api/app/services/draft_desk.py.
    """
    stage = str(assignment_context.get("stage") or "")
    topic = str(assignment_context.get("topic") or "").strip()
    target_length = assignment_context.get("target_length_seconds")
    try:
        length = int(target_length) if target_length is not None else None
    except (TypeError, ValueError):
        length = None

    if stage == "review":
        return False, None, "review stage is human-gated; workers must not execute it"

    if stage in {"scripting", "idea"}:
        if not topic:
            return False, None, "draft_desk requires topic in assignment context"
        cleaned = " ".join(topic.split())
        business = " ".join(str(assignment_context.get("business_name") or "").split())
        offer = " ".join(str(assignment_context.get("offer") or "").split())
        audience = " ".join(
            str(assignment_context.get("target_audience") or "").split()
        )
        voice = " ".join(str(assignment_context.get("brand_voice") or "").split())
        goal = " ".join(str(assignment_context.get("content_goal") or "").split())
        platform = " ".join(
            str(assignment_context.get("target_platform") or "").split()
        )
        audience_label = audience or "your audience"
        hook = f"{audience_label}: what if {cleaned} is the next step you have been missing?"
        length_note = (
            f"Aim for about {length} seconds."
            if length is not None
            else "Keep the piece concise and skimmable."
        )
        context_lines = [
            f"Business: {business}." if business else "",
            f"Offer: {offer}." if offer else "",
            f"Audience: {audience}." if audience else "",
            f"Brand voice: {voice}." if voice else "",
            f"Content goal: {goal}." if goal else "",
            f"Intended platform: {platform}." if platform else "",
        ]
        context = "\n".join(line for line in context_lines if line)
        context_block = f"{context}\n\n" if context else "\n"
        body = (
            f"{hook}\n\n"
            f"Today we unpack {cleaned}. {length_note}\n"
            f"{context_block}"
            f"1) Why {cleaned} matters now\n"
            f"2) The mistake {audience_label} commonly makes\n"
            f"3) A practical next step you can take today\n\n"
            f"Close with a clear takeaway your viewer can repeat."
        )
        if offer and business:
            cta = f"If you want help with {offer}, contact {business} and take the next step."
        elif offer:
            cta = f"If you want help with {offer}, take the next step today."
        else:
            cta = f"If this helped, save it and try one change around {cleaned} this week."
        return (
            True,
            {
                "provider": "draft_desk",
                "script_hook": hook,
                "script_body": body,
                "script_cta": cta,
                "estimated_cost_usd": "0.00",
                "topic": cleaned,
            },
            "",
        )

    return (
        True,
        {
            "provider": "draft_desk",
            "stage": stage,
            "summary": f"Draft Desk completed stage '{stage}' for topic '{topic or 'n/a'}'.",
            "estimated_cost_usd": "0.00",
        },
        "",
    )
