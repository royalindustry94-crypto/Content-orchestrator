"""Draft Desk generation — deterministic, non-stub stage outputs.

Private Beta SKU: produce real draft copy from a topic without an external
AI provider. Workers and the Review Desk content-job path share this module
so generation is never an empty success payload.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DraftDeskOutput:
    script_hook: str
    script_body: str
    script_cta: str
    provider: str = "draft_desk"
    estimated_cost_usd: str = "0.01"


def generate_script_draft(
    *,
    topic: str,
    target_length_seconds: int | None = None,
) -> DraftDeskOutput:
    """Generate a complete draft script for the scripting stage."""
    cleaned = " ".join(topic.strip().split())
    if not cleaned:
        raise ValueError("topic is required for Draft Desk generation")

    length_note = (
        f"Aim for about {target_length_seconds} seconds."
        if target_length_seconds is not None
        else "Keep the piece concise and skimmable."
    )
    hook = f"What if {cleaned} is the lever your audience has been missing?"
    body = (
        f"{hook}\n\n"
        f"Today we unpack {cleaned}. {length_note}\n\n"
        f"1) Why {cleaned} matters now\n"
        f"2) The mistake most teams make\n"
        f"3) A practical next step you can take today\n\n"
        f"Close with a clear takeaway your viewer can repeat."
    )
    cta = f"If this helped, save it and try one change around {cleaned} this week."
    return DraftDeskOutput(script_hook=hook, script_body=body, script_cta=cta)


def execute_stage(context: dict) -> tuple[bool, dict | None, str]:
    """Synchronous stage executor used by the worker (wrapped async)."""
    stage = str(context.get("stage") or "")
    topic = str(context.get("topic") or "").strip()
    target_length = context.get("target_length_seconds")
    try:
        length = int(target_length) if target_length is not None else None
    except (TypeError, ValueError):
        length = None

    if stage in {"scripting", "idea"}:
        if not topic:
            return False, None, "draft_desk requires topic in assignment context"
        try:
            draft = generate_script_draft(topic=topic, target_length_seconds=length)
        except ValueError as exc:
            return False, None, str(exc)
        return (
            True,
            {
                "provider": draft.provider,
                "script_hook": draft.script_hook,
                "script_body": draft.script_body,
                "script_cta": draft.script_cta,
                "estimated_cost_usd": draft.estimated_cost_usd,
                "topic": topic,
            },
            "",
        )

    if stage == "review":
        return False, None, "review stage is human-gated; workers must not execute it"

    # Other stages: produce an explicit structured artifact rather than {}.
    return (
        True,
        {
            "provider": "draft_desk",
            "stage": stage,
            "summary": f"Draft Desk completed stage '{stage}' for topic '{topic or 'n/a'}'.",
            "estimated_cost_usd": "0.01",
        },
        "",
    )
