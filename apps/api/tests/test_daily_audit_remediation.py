from __future__ import annotations

from pathlib import Path

import pytest

from app.services import daily_audit_remediation as audit_module
from app.services.daily_audit_remediation import (
    AuditFinding,
    GateResult,
    can_create_remediation_pr,
    classify_finding,
    compute_verdict,
    maybe_create_remediation_pr,
    remediation_decision,
    render_pdf_lines,
    resolve_audit_ref,
    write_text_pdf,
)


def test_classification_marks_lint_failure_as_deterministic_low_risk():
    finding = classify_finding("api", "Lint", "failure")
    assert finding.severity == "low"
    assert finding.deterministic_repair is True
    assert finding.remediation_command is not None


def test_prohibited_paths_are_blocked_from_auto_fix():
    decision = remediation_decision([
        ".github/workflows/ci.yml",
        "apps/api/app/services/daily_audit_remediation.py",
    ])
    assert decision.allowed is False
    assert "Prohibited paths changed" in decision.reason


def test_pdf_is_valid_and_contains_exact_sha_and_verdict(tmp_path: Path):
    sha = "0123456789abcdef0123456789abcdef01234567"
    verdict = "CONDITIONAL"
    lines = render_pdf_lines(
        repository="royalindustry94-crypto/Content-orchestrator",
        branch="main",
        sha=sha,
        audited_at_utc="2024-09-04T00:00:00+00:00",
        verdict=verdict,
        gate_results=[GateResult(name="api", conclusion="success", critical=True)],
        findings=[
            AuditFinding(
                code="gate_web_failure",
                severity="high",
                summary="Non-deterministic or unsafe failure in web",
                gate="web",
            )
        ],
        changes_summary=["No previous known-good SHA found."],
    )

    output = tmp_path / "audit.pdf"
    write_text_pdf(lines, output)
    payload = output.read_bytes()

    assert payload.startswith(b"%PDF-1.4")
    assert b"trailer" in payload
    assert sha.encode("ascii") in payload
    assert f"Verdict: {verdict}".encode("ascii") in payload


def test_failed_critical_gate_cannot_create_merge_ready_pr():
    findings = [
        AuditFinding(
            code="gate_security_failure",
            severity="critical",
            summary="Critical gate failed: security",
            gate="security",
        ),
        AuditFinding(
            code="autofix_web_lint",
            severity="low",
            summary="Deterministic lint/format failure in web",
            gate="web",
            deterministic_repair=True,
            remediation_command=(("npm", "run", "lint", "--", "--fix"),),
        ),
    ]

    assert can_create_remediation_pr(findings) is False


def test_medium_finding_forces_conditional_verdict():
    findings = [
        AuditFinding(
            code="unknown_signal",
            severity="medium",
            summary="requires human follow-up",
            gate="audit",
        )
    ]
    assert compute_verdict(findings) == "CONDITIONAL"


def test_resolve_audit_ref_uses_github_ref_name(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("AUDIT_REF", raising=False)
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    assert resolve_audit_ref(tmp_path) == "main"


def test_resolve_audit_ref_prefers_head_ref(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("AUDIT_REF", raising=False)
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    monkeypatch.setenv("GITHUB_HEAD_REF", "feature/safe-change")
    assert resolve_audit_ref(tmp_path) == "feature/safe-change"


def test_resolve_audit_ref_prefers_explicit_audit_ref(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("AUDIT_REF", "release/main")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    monkeypatch.setenv("GITHUB_HEAD_REF", "feature/safe-change")
    assert resolve_audit_ref(tmp_path) == "release/main"


def test_resolve_audit_ref_falls_back_to_git_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.delenv("AUDIT_REF", raising=False)
    monkeypatch.delenv("GITHUB_REF_NAME", raising=False)
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    monkeypatch.setattr(audit_module, "git_current_branch", lambda _repo_root: "main")
    assert resolve_audit_ref(tmp_path) == "main"


def test_refuse_pr_creation_when_git_push_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    class FakeClient:
        created = False

        @staticmethod
        def list_pulls_with_head(owner: str, branch: str):
            return []

        @classmethod
        def create_pull_request(cls, title: str, head: str, base: str, body: str):
            cls.created = True
            return {"html_url": "https://example.test/pr/1"}

    monkeypatch.setattr(audit_module, "git_changed_paths", lambda _repo_root: ["docs/notes.md"])

    def _run_checked(command: list[str], cwd: Path, *, reason: str):
        if command[:2] == ["git", "push"]:
            raise RuntimeError("push failed")
        return None

    monkeypatch.setattr(audit_module, "run_checked_command", _run_checked)

    findings = [
        AuditFinding(
            code="autofix_api_lint",
            severity="low",
            summary="Deterministic lint/format failure in api",
            gate="api",
            deterministic_repair=True,
            remediation_command=(("ruff", "check", ".", "--fix"),),
        )
    ]

    with pytest.raises(RuntimeError, match="push failed"):
        maybe_create_remediation_pr(
            repo_root=tmp_path,
            owner="royalindustry94-crypto",
            base_branch="main",
            audited_branch="feature/safe-change",
            sha="0123456789abcdef0123456789abcdef01234567",
            findings=findings,
            client=FakeClient(),
        )

    assert FakeClient.created is False


def test_auto_remediation_branch_cannot_spawn_follow_up_pr(tmp_path: Path):
    class FakeClient:
        @staticmethod
        def list_pulls_with_head(owner: str, branch: str):
            return []

        @staticmethod
        def create_pull_request(title: str, head: str, base: str, body: str):
            raise AssertionError("should not create PR from auto-remediation branch")

    findings = [
        AuditFinding(
            code="autofix_web_lint",
            severity="low",
            summary="Deterministic lint/format failure in web",
            gate="web",
            deterministic_repair=True,
            remediation_command=(("npm", "run", "lint", "--", "--fix"),),
        )
    ]

    created = maybe_create_remediation_pr(
        repo_root=tmp_path,
        owner="royalindustry94-crypto",
        base_branch="main",
        audited_branch="auto-remediation/123-abc",
        sha="0123456789abcdef0123456789abcdef01234567",
        findings=findings,
        client=FakeClient(),
    )
    assert created is None
