from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class GateResult:
    name: str
    conclusion: str
    critical: bool
    details: str | None = None


@dataclasses.dataclass(frozen=True)
class AuditFinding:
    code: str
    severity: str
    summary: str
    gate: str
    deterministic_repair: bool = False
    remediation_command: tuple[str, ...] | None = None


@dataclasses.dataclass(frozen=True)
class RemediationDecision:
    allowed: bool
    reason: str


PROHIBITED_PATH_PREFIXES = (
    ".github/",
    "apps/api/alembic/",
    "apps/api/app/api/routes/auth.py",
    "apps/api/app/api/routes/review_gates.py",
    "apps/api/app/core/",
    "apps/api/app/db/",
    "apps/api/app/models/",
    "apps/api/app/services/billing.py",
    "apps/api/app/services/publication_policy.py",
    "apps/api/app/services/spend",
)

ALLOWED_REMEDIATION_PATTERNS = (
    re.compile(r"^docs/.+\\.md$"),
    re.compile(r"^.+\\.md$"),
    re.compile(r"^.+\\.(py|ts|tsx|js|jsx|json|yml|yaml|snap)$"),
)

SAFE_AUTOFIX_STEPS: dict[tuple[str, str], tuple[str, ...]] = {
    ("api", "Lint"): ("pip", "install", "-e", ".[dev]", "&&", "ruff", "check", ".", "--fix"),
    ("worker", "Lint"): ("pip", "install", "-e", ".[dev]", "&&", "ruff", "check", ".", "--fix"),
    ("web", "Lint"): ("npm", "ci", "&&", "npm", "run", "lint", "--", "--fix"),
}

CRITICAL_GATES = frozenset({"security", "browser-smoke", "docker-build", "api"})


class GitHubClient:
    def __init__(self, token: str, owner: str, repo: str):
        self._token = token
        self._base = f"https://api.github.com/repos/{owner}/{repo}"

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = None
        headers = {
            "Authorization": "Bearer " + self._token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"{self._base}{path}",
            method=method,
            headers=headers,
            data=data,
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API {method} {path} failed: {exc.code} {body}") from exc

    def list_workflow_runs(
        self,
        workflow: str,
        event: str | None = None,
        branch: str | None = None,
    ) -> list[dict]:
        params = {"per_page": "20"}
        if event:
            params["event"] = event
        if branch:
            params["branch"] = branch
        query = urllib.parse.urlencode(params)
        payload = self._request("GET", f"/actions/workflows/{workflow}/runs?{query}")
        return payload.get("workflow_runs", [])

    def dispatch_workflow(self, workflow: str, ref: str) -> None:
        self._request("POST", f"/actions/workflows/{workflow}/dispatches", {"ref": ref})

    def list_jobs(self, run_id: int) -> list[dict]:
        payload = self._request("GET", f"/actions/runs/{run_id}/jobs?per_page=100")
        return payload.get("jobs", [])

    def list_pulls_with_head(self, owner: str, branch: str) -> list[dict]:
        query = urllib.parse.urlencode(
            {"state": "all", "head": f"{owner}:{branch}", "per_page": "10"}
        )
        payload = self._request("GET", f"/pulls?{query}")
        return payload if isinstance(payload, list) else []

    def create_pull_request(self, title: str, head: str, base: str, body: str) -> dict:
        return self._request(
            "POST",
            "/pulls",
            {"title": title, "head": head, "base": base, "body": body, "draft": True},
        )


def run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def is_prohibited_path(path: str) -> bool:
    normalized = path[2:] if path.startswith("./") else path
    return any(normalized.startswith(prefix) for prefix in PROHIBITED_PATH_PREFIXES)


def is_allowed_remediation_path(path: str) -> bool:
    normalized = path[2:] if path.startswith("./") else path
    if is_prohibited_path(normalized):
        return False
    return any(pattern.match(normalized) for pattern in ALLOWED_REMEDIATION_PATTERNS)


def classify_finding(gate_name: str, step_name: str | None, conclusion: str) -> AuditFinding:
    code = f"gate_{gate_name}_{conclusion}"
    if conclusion == "success":
        return AuditFinding(code=code, severity="info", summary="Gate passed", gate=gate_name)

    key = (gate_name, step_name or "")
    command = SAFE_AUTOFIX_STEPS.get(key)
    if command:
        return AuditFinding(
            code=f"autofix_{gate_name}_{(step_name or '').lower().replace(' ', '_')}",
            severity="low",
            summary=f"Deterministic lint/format failure in {gate_name}",
            gate=gate_name,
            deterministic_repair=True,
            remediation_command=command,
        )

    if gate_name in CRITICAL_GATES:
        return AuditFinding(
            code=code,
            severity="critical",
            summary=f"Critical gate failed: {gate_name}",
            gate=gate_name,
        )

    return AuditFinding(
        code=code,
        severity="high",
        summary=f"Non-deterministic or unsafe failure in {gate_name}",
        gate=gate_name,
    )


def remediation_fingerprint(sha: str, finding: AuditFinding) -> str:
    raw = f"{sha}:{finding.code}:{finding.gate}:{finding.summary}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def remediation_decision(changed_paths: list[str]) -> RemediationDecision:
    if not changed_paths:
        return RemediationDecision(False, "No changes produced by remediation")

    prohibited = [path for path in changed_paths if is_prohibited_path(path)]
    if prohibited:
        changed = ", ".join(sorted(prohibited))
        return RemediationDecision(False, f"Prohibited paths changed: {changed}")

    disallowed = [path for path in changed_paths if not is_allowed_remediation_path(path)]
    if disallowed:
        changed = ", ".join(sorted(disallowed))
        return RemediationDecision(False, f"Paths outside allowlist: {changed}")

    return RemediationDecision(True, "Changes are within remediation allowlist")


def can_create_remediation_pr(findings: list[AuditFinding]) -> bool:
    if any(f.severity in {"critical", "high", "medium"} for f in findings):
        return False
    return any(f.deterministic_repair for f in findings)


def summarize_changes(repo_root: Path, last_good_sha: str | None, current_sha: str) -> list[str]:
    if not last_good_sha:
        return ["No previous known-good SHA found."]

    commits = run_command(
        ["git", "log", "--oneline", f"{last_good_sha}..{current_sha}", "--max-count", "20"],
        cwd=repo_root,
    )
    files = run_command(
        ["git", "diff", "--name-status", f"{last_good_sha}..{current_sha}"],
        cwd=repo_root,
    )
    lines = [f"Last known-good SHA: {last_good_sha}"]
    if commits.stdout.strip():
        lines.append("Commits since last known-good:")
        lines.extend(f"  {line}" for line in commits.stdout.strip().splitlines())
    if files.stdout.strip():
        lines.append("File changes since last known-good:")
        lines.extend(f"  {line}" for line in files.stdout.strip().splitlines()[:50])
    return lines


def compute_verdict(findings: list[AuditFinding]) -> str:
    if any(f.severity == "critical" for f in findings):
        return "FAIL"
    if any(f.severity == "high" for f in findings):
        return "CONDITIONAL"
    return "PASS"


def findings_by_severity(findings: list[AuditFinding]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_text_pdf(lines: list[str], output_path: Path) -> None:
    page_line_limit = 44
    chunks = [
        lines[index : index + page_line_limit]
        for index in range(0, len(lines), page_line_limit)
    ]
    if not chunks:
        chunks = [["(empty report)"]]

    objects: list[bytes] = []

    def add_object(payload: str) -> int:
        objects.append(payload.encode("latin-1", errors="replace"))
        return len(objects)

    page_ids: list[int] = []
    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for chunk in chunks:
        text_ops = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
        for line in chunk:
            text_ops.append(f"({_escape_pdf_text(line)}) Tj")
            text_ops.append("T*")
        text_ops.append("ET")
        stream = "\n".join(text_ops)
        content_length = len(stream.encode("latin-1", errors="replace"))
        content_id = add_object(
            f"<< /Length {content_length} >>\nstream\n{stream}\nendstream"
        )
        page_id = add_object(
            "<< /Type /Page /Parent 0 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    pages_kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_id = add_object(f"<< /Type /Pages /Kids [{pages_kids}] /Count {len(page_ids)} >>")

    for page_id in page_ids:
        page_payload = objects[page_id - 1].decode("latin-1", errors="replace")
        page_payload = page_payload.replace("/Parent 0 0 R", f"/Parent {pages_id} 0 R")
        objects[page_id - 1] = page_payload.encode("latin-1", errors="replace")

    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        handle.write(b"%PDF-1.4\n")
        offsets = [0]
        for idx, obj in enumerate(objects, start=1):
            offsets.append(handle.tell())
            handle.write(f"{idx} 0 obj\n".encode("ascii"))
            handle.write(obj)
            handle.write(b"\nendobj\n")

        xref_offset = handle.tell()
        handle.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        handle.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            handle.write(f"{offset:010d} 00000 n \n".encode("ascii"))

        handle.write(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF\n"
            ).encode("ascii")
        )


def render_pdf_lines(
    *,
    repository: str,
    branch: str,
    sha: str,
    audited_at_utc: str,
    verdict: str,
    gate_results: list[GateResult],
    findings: list[AuditFinding],
    changes_summary: list[str],
) -> list[str]:
    counts = findings_by_severity(findings)
    lines = [
        "Content Orchestrator Daily Audit",
        f"Repository: {repository}",
        f"Branch: {branch}",
        f"SHA: {sha}",
        f"Date (UTC): {audited_at_utc}",
        "",
        "Gate Results:",
    ]
    for gate in gate_results:
        details = f" ({gate.details})" if gate.details else ""
        lines.append(f"- {gate.name}: {gate.conclusion}{details}")

    lines.extend(
        [
            "",
            "Findings by severity:",
            f"- critical: {counts.get('critical', 0)}",
            f"- high: {counts.get('high', 0)}",
            f"- medium: {counts.get('medium', 0)}",
            f"- low: {counts.get('low', 0)}",
            f"- info: {counts.get('info', 0)}",
            "",
            "Findings:",
        ]
    )
    for finding in findings:
        lines.append(f"- [{finding.severity}] {finding.code}: {finding.summary}")

    lines.extend(["", "Change summary:"])
    lines.extend(f"- {entry}" for entry in changes_summary)
    lines.extend(["", f"Verdict: {verdict}"])
    return lines


def git_changed_paths(repo_root: Path) -> list[str]:
    result = run_command(["git", "diff", "--name-only"], cwd=repo_root)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def git_current_sha(repo_root: Path) -> str:
    result = run_command(["git", "rev-parse", "HEAD"], cwd=repo_root)
    sha = result.stdout.strip()
    if not sha:
        raise RuntimeError("Unable to determine HEAD SHA")
    return sha


def git_current_branch(repo_root: Path) -> str:
    result = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    branch = result.stdout.strip()
    if not branch:
        raise RuntimeError("Unable to determine branch name")
    return branch


def find_failed_step(job: dict) -> str | None:
    for step in job.get("steps", []):
        if step.get("conclusion") == "failure":
            return step.get("name")
    return None


def wait_for_dispatched_run(
    client: GitHubClient,
    workflow_file: str,
    sha: str,
    branch: str,
    timeout_seconds: int = 5400,
) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        runs = client.list_workflow_runs(workflow_file, event="workflow_dispatch", branch=branch)
        for run in runs:
            if run.get("head_sha") != sha:
                continue
            status = run.get("status")
            if status == "completed":
                return run
        time.sleep(20)
    raise TimeoutError("Timed out waiting for dispatched CI run completion")


def find_last_known_good_sha(
    client: GitHubClient,
    workflow_file: str,
    branch: str,
    current_sha: str,
) -> str | None:
    runs = client.list_workflow_runs(workflow_file, event=None, branch=branch)
    for run in runs:
        if run.get("conclusion") == "success" and run.get("head_sha") != current_sha:
            return run.get("head_sha")
    return None


def perform_remediation(
    *,
    repo_root: Path,
    api_root: Path,
    worker_root: Path,
    web_root: Path,
    findings: list[AuditFinding],
) -> list[str]:
    changed_before = set(git_changed_paths(repo_root))
    for finding in findings:
        if not finding.deterministic_repair or not finding.remediation_command:
            continue
        if finding.gate == "api":
            cwd = api_root
        elif finding.gate == "worker":
            cwd = worker_root
        else:
            cwd = web_root
        command = ["bash", "-lc", " ".join(finding.remediation_command)]
        run_command(command, cwd=cwd)

    changed_after = set(git_changed_paths(repo_root))
    return sorted(changed_after - changed_before)


def maybe_create_remediation_pr(
    *,
    repo_root: Path,
    owner: str,
    base_branch: str,
    sha: str,
    findings: list[AuditFinding],
    client: GitHubClient,
) -> str | None:
    if not can_create_remediation_pr(findings):
        return None

    deterministic = [finding for finding in findings if finding.deterministic_repair]
    fingerprint = remediation_fingerprint(sha, deterministic[0])
    branch = f"auto-remediation/{sha[:12]}-{fingerprint[:8]}"
    if client.list_pulls_with_head(owner, branch):
        return None

    changed_paths = git_changed_paths(repo_root)
    decision = remediation_decision(changed_paths)
    if not decision.allowed:
        return None

    run_command(["git", "checkout", "-b", branch], cwd=repo_root)
    run_command(["git", "add", "--"] + changed_paths, cwd=repo_root)
    run_command(
        [
            "git",
            "commit",
            "-m",
            f"chore: safe deterministic remediation for {sha[:12]}",
        ],
        cwd=repo_root,
    )
    run_command(["git", "push", "origin", branch], cwd=repo_root)

    pr = client.create_pull_request(
        title=f"[Auto-remediation][draft] Safe fixes for {sha[:12]}",
        head=branch,
        base=base_branch,
        body=(
            "Automated low-risk deterministic remediation from daily audit worker.\n\n"
            "This PR is intentionally draft and must not be auto-merged."
        ),
    )
    return pr.get("html_url")


def run_audit() -> int:
    parser = argparse.ArgumentParser(description="Daily audit and safe-remediation worker")
    parser.add_argument("--output-pdf", required=True, help="Path to output PDF artifact")
    parser.add_argument("--ci-workflow", default="ci.yml")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repository:
        raise RuntimeError("GITHUB_TOKEN and GITHUB_REPOSITORY are required")

    owner, repo = repository.split("/", maxsplit=1)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[4]
    api_root = repo_root / "apps" / "api"
    worker_root = repo_root / "apps" / "worker"
    web_root = repo_root / "apps" / "web"

    sha = git_current_sha(repo_root)
    branch = git_current_branch(repo_root)

    client = GitHubClient(token=token, owner=owner, repo=repo)

    last_known_good_sha = find_last_known_good_sha(
        client,
        "daily-audit-remediation.yml",
        branch,
        sha,
    )

    client.dispatch_workflow(args.ci_workflow, ref=branch)
    ci_run = wait_for_dispatched_run(client, args.ci_workflow, sha, branch)
    ci_jobs = client.list_jobs(int(ci_run["id"]))

    findings: list[AuditFinding] = []
    gate_results: list[GateResult] = []
    for job in ci_jobs:
        name = str(job.get("name"))
        conclusion = str(job.get("conclusion") or "unknown")
        failed_step = find_failed_step(job)
        gate_results.append(
            GateResult(
                name=name,
                conclusion=conclusion,
                critical=name in CRITICAL_GATES,
                details=f"failed_step={failed_step}" if failed_step else None,
            )
        )
        findings.append(classify_finding(name, failed_step, conclusion))

    remediation_candidates = [finding for finding in findings if finding.deterministic_repair]
    if remediation_candidates and can_create_remediation_pr(findings):
        changed = perform_remediation(
            repo_root=repo_root,
            api_root=api_root,
            worker_root=worker_root,
            web_root=web_root,
            findings=remediation_candidates,
        )
        if changed:
            maybe_create_remediation_pr(
                repo_root=repo_root,
                owner=owner,
                base_branch="main",
                sha=sha,
                findings=remediation_candidates,
                client=client,
            )

    verdict = compute_verdict(findings)
    changes_summary = summarize_changes(repo_root, last_known_good_sha, sha)
    audited_at_utc = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    lines = render_pdf_lines(
        repository=repository,
        branch=branch,
        sha=sha,
        audited_at_utc=audited_at_utc,
        verdict=verdict,
        gate_results=gate_results,
        findings=findings,
        changes_summary=changes_summary,
    )
    write_text_pdf(lines, Path(args.output_pdf))

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as handle:
            handle.write(f"Daily audit completed for `{sha}` with verdict **{verdict}**.\n")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(run_audit())
    except Exception as exc:
        print(f"daily_audit_remediation error: {exc}", file=sys.stderr)
        raise
