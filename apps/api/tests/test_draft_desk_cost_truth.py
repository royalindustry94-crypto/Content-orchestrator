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


def test_worker_stage_path_keeps_saved_profile_context() -> None:
    ok, result, error = execute_stage(
        {
            "stage": "scripting",
            "topic": "weekly planning",
            "business_name": "North Star Studio",
            "offer": "content strategy",
            "target_audience": "independent consultants",
            "brand_voice": "direct and practical",
            "content_goal": "generate qualified enquiries",
            "target_platform": "LinkedIn",
        }
    )

    assert ok is True
    assert error == ""
    assert result is not None
    assert "Business: North Star Studio." in result["script_body"]
    assert "Audience: independent consultants." in result["script_body"]
    assert "Intended platform: LinkedIn." in result["script_body"]
    assert "contact North Star Studio" in result["script_cta"]
