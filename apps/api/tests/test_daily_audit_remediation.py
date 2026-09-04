from __future__ import annotations

from pathlib import Path

from app.services.daily_audit_remediation import (
    AuditFinding,
    GateResult,
    can_create_remediation_pr,
    classify_finding,
    remediation_decision,
    render_pdf_lines,
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
        audited_at_utc="2026-09-04T00:00:00+00:00",
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
            remediation_command=("npm", "run", "lint", "--", "--fix"),
        ),
    ]

    assert can_create_remediation_pr(findings) is False
