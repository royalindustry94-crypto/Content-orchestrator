from app.services.draft_desk import execute_stage, generate_script_draft


def test_local_draft_generation_reports_zero_external_provider_cost() -> None:
    draft = generate_script_draft(topic="A useful business lesson")
    assert draft.provider == "draft_desk"
    assert draft.estimated_cost_usd == "0.00"

    ok, result, error = execute_stage(
        {"stage": "scripting", "topic": "A useful business lesson"}
    )
    assert ok is True
    assert error == ""
    assert result is not None
    assert result["estimated_cost_usd"] == "0.00"
