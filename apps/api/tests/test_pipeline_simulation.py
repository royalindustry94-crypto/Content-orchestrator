"""End-to-end coverage for the simulation pipeline provider.

These tests drive the same HTTP routes an operator uses, with
``PIPELINE_PROVIDER_MODE=simulation``, and assert that the independent audit
gates still decide for themselves rather than rubber-stamping provider output.
"""

from __future__ import annotations

import uuid
from urllib.parse import urlsplit

import pytest

from app.core.config import get_settings
from app.providers import get_pipeline_provider


@pytest.fixture
def simulation_mode(monkeypatch):
    """Run the enclosed test with the simulation provider configured."""
    monkeypatch.setenv("PIPELINE_PROVIDER_MODE", "simulation")
    get_settings.cache_clear()
    get_pipeline_provider.cache_clear()
    yield
    monkeypatch.delenv("PIPELINE_PROVIDER_MODE", raising=False)
    get_settings.cache_clear()
    get_pipeline_provider.cache_clear()


async def _workspace(client, headers) -> str:
    response = await client.post(
        "/workspaces", json={"name": f"sim-{uuid.uuid4().hex[:8]}"}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _audited_opportunity(client, headers, workspace_id, objective) -> str:
    run = await client.post(
        f"/workspaces/{workspace_id}/research/runs",
        json={"research_objective": objective},
        headers=headers,
    )
    assert run.status_code == 201, run.text
    opportunities = await client.get(
        f"/workspaces/{workspace_id}/research/opportunities", headers=headers
    )
    opportunity_id = opportunities.json()[0]["id"]
    audit = await client.post(
        f"/workspaces/{workspace_id}/research/opportunities/{opportunity_id}/audit",
        headers=headers,
    )
    assert audit.json()["state"] == "pass", audit.text
    return opportunity_id


async def _audited_brief(client, headers, workspace_id, objective) -> str:
    opportunity_id = await _audited_opportunity(client, headers, workspace_id, objective)
    run = await client.post(
        f"/workspaces/{workspace_id}/strategy/runs",
        json={
            "strategy_objective": f"Turn '{objective}' into a short explainer",
            "source_opportunity_ids": [opportunity_id],
        },
        headers=headers,
    )
    assert run.status_code == 201, run.text
    briefs = await client.get(f"/workspaces/{workspace_id}/strategy/briefs", headers=headers)
    brief_id = briefs.json()[0]["id"]
    audit = await client.post(
        f"/workspaces/{workspace_id}/strategy/briefs/{brief_id}/audit", headers=headers
    )
    assert audit.json()["state"] == "pass", audit.text
    return brief_id


async def _audited_package(client, headers, workspace_id, objective) -> str:
    brief_id = await _audited_brief(client, headers, workspace_id, objective)
    run = await client.post(
        f"/workspaces/{workspace_id}/content-department/runs",
        json={"strategy_brief_id": brief_id},
        headers=headers,
    )
    assert run.status_code == 201, run.text
    packages = await client.get(
        f"/workspaces/{workspace_id}/content-department/packages", headers=headers
    )
    package_id = packages.json()[0]["id"]
    audits = await client.post(
        f"/workspaces/{workspace_id}/content-department/packages/{package_id}/audits",
        headers=headers,
    )
    assert audits.status_code == 200, audits.text
    return package_id


async def test_research_run_produces_audited_opportunity(client, new_user, simulation_mode):
    _, _, headers = new_user
    workspace_id = await _workspace(client, headers)

    run = await client.post(
        f"/workspaces/{workspace_id}/research/runs",
        json={"research_objective": "How teams adopt evidence-led short form content"},
        headers=headers,
    )
    assert run.status_code == 201, run.text
    body = run.json()
    assert body["status"] == "succeeded"
    assert body["provider_state"] == "simulation"

    opportunities = await client.get(
        f"/workspaces/{workspace_id}/research/opportunities", headers=headers
    )
    assert opportunities.status_code == 200
    items = opportunities.json()
    assert len(items) == 1
    opportunity_id = items[0]["id"]

    audit = await client.post(
        f"/workspaces/{workspace_id}/research/opportunities/{opportunity_id}/audit",
        headers=headers,
    )
    assert audit.status_code == 200, audit.text
    # The auditor inspects stored provenance independently; a clean pass here
    # means the simulated sources really carry distinct, accepted evidence.
    assert audit.json()["state"] == "pass"


async def test_research_sources_are_never_mistaken_for_real_citations(
    client, new_user, simulation_mode
):
    _, _, headers = new_user
    workspace_id = await _workspace(client, headers)

    await client.post(
        f"/workspaces/{workspace_id}/research/runs",
        json={"research_objective": "Evidence-led short form content"},
        headers=headers,
    )
    opportunities = await client.get(
        f"/workspaces/{workspace_id}/research/opportunities", headers=headers
    )
    opportunity_id = opportunities.json()[0]["id"]
    sources = await client.get(
        f"/workspaces/{workspace_id}/research/opportunities/{opportunity_id}/sources",
        headers=headers,
    )
    assert sources.status_code == 200
    urls = [item["source"]["canonical_url"] for item in sources.json()]
    assert urls
    # RFC 2606 reserves .invalid precisely so these can never resolve.
    assert all(urlsplit(url).hostname.endswith(".invalid") for url in urls)


async def test_repeated_identical_run_is_detected_as_duplicate(client, new_user, simulation_mode):
    _, _, headers = new_user
    workspace_id = await _workspace(client, headers)
    payload = {"research_objective": "A stable objective for duplicate detection"}

    first = await client.post(
        f"/workspaces/{workspace_id}/research/runs", json=payload, headers=headers
    )
    assert first.json()["opportunity_count"] == 1
    second = await client.post(
        f"/workspaces/{workspace_id}/research/runs", json=payload, headers=headers
    )
    # Deterministic output must dedupe rather than pile up near-identical work.
    assert second.json()["opportunity_count"] == 0


async def test_strategy_requires_research_pass_even_in_simulation(
    client, new_user, simulation_mode
):
    _, _, headers = new_user
    workspace_id = await _workspace(client, headers)
    await client.post(
        f"/workspaces/{workspace_id}/research/runs",
        json={"research_objective": "Gate check for unaudited opportunities"},
        headers=headers,
    )
    opportunities = await client.get(
        f"/workspaces/{workspace_id}/research/opportunities", headers=headers
    )
    opportunity_id = opportunities.json()[0]["id"]

    # No Research Auditor pass yet, so the Strategist handoff must be refused.
    blocked = await client.post(
        f"/workspaces/{workspace_id}/strategy/runs",
        json={
            "strategy_objective": "Turn the finding into a short explainer",
            "source_opportunity_ids": [opportunity_id],
        },
        headers=headers,
    )
    assert blocked.status_code == 409, blocked.text


async def test_strategy_brief_passes_independent_auditor(client, new_user, simulation_mode):
    _, _, headers = new_user
    workspace_id = await _workspace(client, headers)
    await client.post(
        f"/workspaces/{workspace_id}/research/runs",
        json={"research_objective": "Adoption patterns for evidence-led explainers"},
        headers=headers,
    )
    opportunities = await client.get(
        f"/workspaces/{workspace_id}/research/opportunities", headers=headers
    )
    opportunity_id = opportunities.json()[0]["id"]
    await client.post(
        f"/workspaces/{workspace_id}/research/opportunities/{opportunity_id}/audit",
        headers=headers,
    )

    run = await client.post(
        f"/workspaces/{workspace_id}/strategy/runs",
        json={
            "strategy_objective": "Turn the finding into a short explainer",
            "source_opportunity_ids": [opportunity_id],
        },
        headers=headers,
    )
    assert run.status_code == 201, run.text
    assert run.json()["status"] == "succeeded"

    briefs = await client.get(f"/workspaces/{workspace_id}/strategy/briefs", headers=headers)
    assert briefs.status_code == 200
    brief_id = briefs.json()[0]["id"]

    audit = await client.post(
        f"/workspaces/{workspace_id}/strategy/briefs/{brief_id}/audit", headers=headers
    )
    assert audit.status_code == 200, audit.text
    assert audit.json()["state"] == "pass", audit.text


async def test_all_four_content_auditors_pass_and_open_producer_gate(
    client, new_user, simulation_mode
):
    _, _, headers = new_user
    workspace_id = await _workspace(client, headers)
    brief_id = await _audited_brief(client, headers, workspace_id, "Content auditors clean path")

    run = await client.post(
        f"/workspaces/{workspace_id}/content-department/runs",
        json={"strategy_brief_id": brief_id},
        headers=headers,
    )
    assert run.status_code == 201, run.text
    packages = await client.get(
        f"/workspaces/{workspace_id}/content-department/packages", headers=headers
    )
    package_id = packages.json()[0]["id"]

    # Producer handoff must be refused until every mandatory auditor has run.
    premature = await client.get(
        f"/workspaces/{workspace_id}/content-department/packages/{package_id}/producer-gate",
        headers=headers,
    )
    assert premature.status_code == 409, premature.text

    audits = await client.post(
        f"/workspaces/{workspace_id}/content-department/packages/{package_id}/audits",
        headers=headers,
    )
    assert audits.status_code == 200, audits.text
    states = {item["auditor_type"]: item["state"] for item in audits.json()}
    assert states == {
        "language": "pass",
        "fact": "pass",
        "brand": "pass",
        "originality": "pass",
    }, audits.text

    gate = await client.get(
        f"/workspaces/{workspace_id}/content-department/packages/{package_id}/producer-gate",
        headers=headers,
    )
    assert gate.status_code == 200, gate.text
    assert gate.json()["eligible"] is True


async def test_content_auditors_are_independent_of_the_writer(client, new_user, simulation_mode):
    _, _, headers = new_user
    workspace_id = await _workspace(client, headers)
    package_id = await _audited_package(client, headers, workspace_id, "Auditor independence")

    detail = await client.get(
        f"/workspaces/{workspace_id}/content-department/packages/{package_id}", headers=headers
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    producers = {body["package"]["writer_worker_id"], body["direction"]["worker_id"]}
    auditors = {audit["auditor_worker_id"] for audit in body["audits"]}
    assert producers.isdisjoint(auditors)
