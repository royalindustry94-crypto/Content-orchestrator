"""Verify a deployed preview against the controls it must not lose.

Drives the same HTTP routes an operator uses, against a running preview
(tunnelled, Vercel, or local ``scripts/serve_preview.py``), and asserts the
Private Beta invariants hold there rather than only in the test suite:

* readiness and honest automation reporting for the runtime profile
* simulation provider is active and labelled as simulated
* signup / login / workspace creation
* the full Scout -> Strategy -> Content -> Producer -> Compliance -> Chief
  Auditor chain terminates at a Human Review Gate, not at publication
* publication stays blocked after human approval
* a second account cannot see or touch the first account's workspace
* simulated generation commits zero actual spend

Usage:

    python scripts/verify_preview.py https://<preview-host>

Exits non-zero on the first failed check. Creates two throwaway accounts in
whatever database the preview points at, so run it against a test project only.
"""

from __future__ import annotations

import argparse
import secrets
import string
import sys
import uuid

import httpx

TIMEOUT = httpx.Timeout(60.0)
PLATFORM = "youtube_shorts"


def unique_topic() -> str:
    """A distinct topic per run, using letters only.

    Deliberately digit-free: the writer echoes the topic into the script, and
    ``_extract_claims`` classifies any sentence containing a digit as a NUMBER
    claim, which the fact auditor blocks because no verification provider can
    substantiate a quantity. A digit in the topic would therefore stop the
    pipeline at the fact audit — correct behaviour, but not what this script is
    here to exercise.
    """
    suffix = "".join(secrets.choice(string.ascii_lowercase) for _ in range(8))
    return f"Preview check {suffix}"

_failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    mark = "PASS" if condition else "FAIL"
    line = f"[{mark}] {label}"
    if detail:
        line += f" — {detail}"
    print(line, flush=True)
    if not condition:
        _failures.append(label)
    return condition


def require(label: str, condition: bool, detail: str = "") -> None:
    """A check whose failure makes every later step meaningless."""
    if not check(label, condition, detail):
        print(f"\nAborting: {label} is a precondition for the remaining checks.")
        sys.exit(1)


class Preview:
    def __init__(self, base_url: str) -> None:
        self.client = httpx.Client(base_url=base_url.rstrip("/"), timeout=TIMEOUT)

    def close(self) -> None:
        self.client.close()

    def api(self, method: str, path: str, **kw) -> httpx.Response:
        return self.client.request(method, f"/api{path}", **kw)

    def signup(self) -> tuple[str, dict[str, str]]:
        email = f"verify-{uuid.uuid4().hex[:10]}@example.invalid"
        password = f"verify-{secrets.token_urlsafe(18)}"
        created = self.api("POST", "/auth/signup", json={"email": email, "password": password})
        require(
            "signup creates an account",
            created.status_code == 201,
            f"HTTP {created.status_code} {created.text[:160]}",
        )
        logged_in = self.api("POST", "/auth/login", json={"email": email, "password": password})
        require(
            "login returns a token for that account",
            logged_in.status_code == 200,
            f"HTTP {logged_in.status_code} {logged_in.text[:160]}",
        )
        token = logged_in.json()["access_token"]
        return email, {"Authorization": f"Bearer {token}"}

    def workspace(self, headers: dict[str, str]) -> str:
        created = self.api(
            "POST", "/workspaces", json={"name": f"verify-{uuid.uuid4().hex[:8]}"}, headers=headers
        )
        require(
            "workspace creation",
            created.status_code == 201,
            f"HTTP {created.status_code} {created.text[:160]}",
        )
        return created.json()["id"]


def check_platform_state(pv: Preview) -> None:
    ready = pv.api("GET", "/health/ready")
    require(
        "/health/ready reports the database reachable",
        ready.status_code == 200 and ready.json().get("status") == "ok",
        f"HTTP {ready.status_code} {ready.text[:160]}",
    )

    provider = pv.api("GET", "/pipeline/provider")
    require("/pipeline/provider responds", provider.status_code == 200)
    body = provider.json()
    check(
        "provider mode is simulation and labelled simulated",
        body.get("mode") == "simulation" and body.get("simulated") is True,
        str(body),
    )
    check(
        "provider advertises external publishing disabled",
        body.get("external_publishing_enabled") is False,
    )
    check("provider advertises human review required", body.get("human_review_required") is True)

    automation = pv.api("GET", "/health/automation")
    require("/health/automation responds", automation.status_code == 200)
    auto = automation.json()
    profile = auto.get("runtime_profile")
    if profile == "serverless":
        check(
            "serverless runtime reports background loops disabled, not idle",
            auto.get("status") == "disabled"
            and not auto.get("tasks_running")
            and bool(auto.get("disabled_reason"))
            and bool(auto.get("unavailable_capabilities")),
            str(auto.get("status")),
        )
    else:
        check(
            f"runtime profile {profile!r} reports loop state consistently",
            (auto.get("status") == "ok") == bool(auto.get("tasks_running")),
            str(auto.get("status")),
        )
    check(
        "openapi docs are not exposed",
        pv.api("GET", "/openapi.json").status_code == 404,
    )


def run_pipeline(pv: Preview, headers: dict[str, str], workspace: str, topic: str) -> str:
    """Drive Scout -> Chief Auditor. Returns the final artifact id."""
    run = pv.api(
        "POST",
        f"/workspaces/{workspace}/research/runs",
        json={"research_objective": topic},
        headers=headers,
    )
    require(
        "Scout research run succeeds",
        run.status_code == 201,
        f"HTTP {run.status_code} {run.text[:200]}",
    )
    opportunities = pv.api(
        "GET", f"/workspaces/{workspace}/research/opportunities", headers=headers
    )
    require("research produced an opportunity", bool(opportunities.json()), opportunities.text[:160])
    opportunity_id = opportunities.json()[0]["id"]

    audit = pv.api(
        "POST",
        f"/workspaces/{workspace}/research/opportunities/{opportunity_id}/audit",
        headers=headers,
    )
    require(
        "Research Auditor passes",
        audit.json().get("state") == "pass",
        audit.text[:200],
    )

    strategy = pv.api(
        "POST",
        f"/workspaces/{workspace}/strategy/runs",
        json={
            "strategy_objective": f"Turn '{topic}' into a short explainer",
            "source_opportunity_ids": [opportunity_id],
        },
        headers=headers,
    )
    require(
        "Strategy run succeeds",
        strategy.status_code == 201,
        f"HTTP {strategy.status_code} {strategy.text[:200]}",
    )
    briefs = pv.api("GET", f"/workspaces/{workspace}/strategy/briefs", headers=headers)
    require("strategy produced a brief", bool(briefs.json()), briefs.text[:160])
    brief_id = briefs.json()[0]["id"]

    brief_audit = pv.api(
        "POST", f"/workspaces/{workspace}/strategy/briefs/{brief_id}/audit", headers=headers
    )
    require("Strategy Auditor passes", brief_audit.json().get("state") == "pass", brief_audit.text[:200])

    content = pv.api(
        "POST",
        f"/workspaces/{workspace}/content-department/runs",
        json={"strategy_brief_id": brief_id},
        headers=headers,
    )
    require(
        "Content Department run succeeds",
        content.status_code == 201,
        f"HTTP {content.status_code} {content.text[:200]}",
    )
    packages = pv.api("GET", f"/workspaces/{workspace}/content-department/packages", headers=headers)
    require("content package created", bool(packages.json()), packages.text[:160])
    package_id = packages.json()[0]["id"]

    audits = pv.api(
        "POST",
        f"/workspaces/{workspace}/content-department/packages/{package_id}/audits",
        headers=headers,
    )
    require("content audits run", audits.status_code == 200, audits.text[:200])
    states = {a.get("auditor_type"): a.get("state") for a in audits.json()}
    require(
        "all four independent content audits pass",
        set(states) == {"language", "fact", "brand", "originality"}
        and all(state == "pass" for state in states.values()),
        str(states),
    )

    production = pv.api(
        "POST",
        f"/workspaces/{workspace}/production/runs",
        json={
            "content_package_id": package_id,
            "target_platform": PLATFORM,
            "target_format": "vertical_video",
            "target_duration_seconds": 45,
        },
        headers=headers,
    )
    require(
        "Producer run succeeds",
        production.status_code == 201,
        f"HTTP {production.status_code} {production.text[:200]}",
    )
    job_id = production.json()["id"]
    detail = pv.api("GET", f"/workspaces/{workspace}/production/runs/{job_id}", headers=headers)
    require("Producer rendered an artifact", bool(detail.json().get("artifacts")), detail.text[:200])
    artifact_id = detail.json()["artifacts"][0]["id"]

    qa = pv.api(
        "POST",
        f"/workspaces/{workspace}/production/artifacts/{artifact_id}/media-qa",
        headers=headers,
    )
    require("Media QA passes", qa.json().get("status") == "pass", qa.text[:200])

    readiness = pv.api(
        "GET",
        f"/workspaces/{workspace}/production/artifacts/{artifact_id}/readiness",
        headers=headers,
    )
    check(
        "a Media QA pass alone does not look like publish readiness",
        readiness.json().get("status") == "blocked",
        readiness.text[:160],
    )

    compliance = pv.api(
        "POST",
        f"/workspaces/{workspace}/compliance/runs",
        json={"final_artifact_id": artifact_id, "target_platform": PLATFORM},
        headers=headers,
    )
    require(
        "Compliance passes",
        compliance.status_code == 201 and compliance.json().get("status") == "pass",
        compliance.text[:200],
    )

    chief = pv.api(
        "POST",
        f"/workspaces/{workspace}/compliance/artifacts/{artifact_id}/chief-audit",
        headers=headers,
    )
    require(
        "Chief Auditor hands off to human review",
        chief.json().get("status") == "pass_to_human_review",
        chief.text[:200],
    )
    return artifact_id


def check_review_gate_and_publication(
    pv: Preview, headers: dict[str, str], workspace: str, artifact_id: str
) -> None:
    gates = pv.api("GET", f"/workspaces/{workspace}/review-gates", headers=headers)
    require("a Human Review Gate is awaiting a decision", len(gates.json()) == 1, gates.text[:200])
    gate = gates.json()[0]
    check("the gate is awaiting, not auto-decided", gate.get("status") == "awaiting", str(gate.get("status")))
    check("the gate carries the script to review", bool(gate.get("script_body")))

    blocked_before = pv.api(
        "POST",
        f"/workspaces/{workspace}/compliance/artifacts/{artifact_id}"
        f"/publication-eligibility?target_platform={PLATFORM}",
        headers=headers,
    )
    check(
        "publication is ineligible before approval",
        blocked_before.json().get("publication_eligible") is False,
        blocked_before.text[:200],
    )

    decision = pv.api(
        "POST",
        f"/workspaces/{workspace}/review-gates/{gate['id']}/decision",
        json={"approved": True, "notes": "Verified simulated output."},
        headers=headers,
    )
    require(
        "the gate accepts a human approval",
        decision.status_code == 200 and decision.json().get("status") == "approved",
        decision.text[:200],
    )

    after = pv.api(
        "POST",
        f"/workspaces/{workspace}/compliance/artifacts/{artifact_id}"
        f"/publication-eligibility?target_platform={PLATFORM}",
        headers=headers,
    )
    body = after.json()
    check(
        "publication STAYS blocked after human approval",
        body.get("publication_eligible") is False,
        str(body.get("blocking_reasons")),
    )
    check(
        "the block reason is external publishing being disabled",
        "external_publishing_disabled" in (body.get("blocking_reasons") or []),
        str(body.get("blocking_reasons")),
    )


def check_zero_spend(pv: Preview, headers: dict[str, str], workspace: str) -> None:
    spend = pv.api("GET", f"/workspaces/{workspace}/spend", headers=headers)
    require("spend snapshot is readable", spend.status_code == 200, spend.text[:200])
    body = spend.json()
    check(
        "simulated generation committed $0 actual spend today",
        float(body.get("daily_used_usd", -1)) == 0.0,
        f"daily_used_usd={body.get('daily_used_usd')}",
    )
    check(
        "simulated generation committed $0 actual spend this month",
        float(body.get("monthly_used_usd", -1)) == 0.0,
        f"monthly_used_usd={body.get('monthly_used_usd')}",
    )
    check(
        "no spend is left dangling in reserve",
        float(body.get("reserved_usd", -1)) == 0.0,
        f"reserved_usd={body.get('reserved_usd')}",
    )


def check_isolation(pv: Preview, victim_workspace: str, victim_artifact: str) -> None:
    _, attacker = pv.signup()
    attacker_workspace = pv.workspace(attacker)

    listed = pv.api("GET", "/workspaces", headers=attacker)
    ids = {w["id"] for w in listed.json()} if listed.status_code == 200 else set()
    check(
        "a second account cannot see the first account's workspace",
        victim_workspace not in ids,
        f"visible={sorted(ids)}",
    )

    for label, path in (
        ("review gates", f"/workspaces/{victim_workspace}/review-gates"),
        ("spend", f"/workspaces/{victim_workspace}/spend"),
        ("opportunities", f"/workspaces/{victim_workspace}/research/opportunities"),
    ):
        response = pv.api("GET", path, headers=attacker)
        check(
            f"cross-workspace read of {label} is refused",
            response.status_code in {403, 404},
            f"HTTP {response.status_code}",
        )

    crossed = pv.api(
        "POST",
        f"/workspaces/{attacker_workspace}/compliance/artifacts/{victim_artifact}/chief-audit",
        headers=attacker,
    )
    check(
        "another workspace's artifact cannot be pulled into your own",
        crossed.status_code == 404,
        f"HTTP {crossed.status_code}",
    )

    gates = pv.api("GET", f"/workspaces/{attacker_workspace}/review-gates", headers=attacker)
    check(
        "no review gate leaked into the second workspace",
        gates.json() == [],
        gates.text[:160],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Preview origin, e.g. https://example.vercel.app")
    args = parser.parse_args()

    print(f"Verifying {args.base_url}\n")
    pv = Preview(args.base_url)
    try:
        check_platform_state(pv)
        print()
        _, headers = pv.signup()
        workspace = pv.workspace(headers)
        print()
        artifact_id = run_pipeline(pv, headers, workspace, unique_topic())
        print()
        check_review_gate_and_publication(pv, headers, workspace, artifact_id)
        print()
        check_zero_spend(pv, headers, workspace)
        print()
        check_isolation(pv, workspace, artifact_id)
    finally:
        pv.close()

    print()
    if _failures:
        print(f"{len(_failures)} check(s) FAILED:")
        for name in _failures:
            print(f"  - {name}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
