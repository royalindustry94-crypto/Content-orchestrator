"""Live GitHub status for the Founder Control Center.

Calls the GitHub REST API when credentials are configured. Missing
configuration or upstream failures return available=False — never fabricated
commits, PRs, or Actions results.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx

from app.core.config import get_settings
from app.schemas.operations_dashboard import (
    GitHubActionRun,
    GitHubBranchStatus,
    GitHubCommit,
    GitHubOut,
    GitHubPullRequest,
)

logger = logging.getLogger(__name__)

_API = "https://api.github.com"


def _token() -> str | None:
    settings = get_settings()
    return settings.github_token or settings.github_api_token


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def github_status() -> GitHubOut:
    settings = get_settings()
    now = datetime.now(UTC)
    token = _token()
    repo = (settings.github_repository or "").strip() or None
    deploy_branch = settings.deployment_git_branch
    deploy_sha = settings.deployment_commit_sha
    deploy_ci = (settings.deployment_ci_status or "unavailable").strip().lower()

    branch_fallback = GitHubBranchStatus(
        name=deploy_branch,
        sha=deploy_sha,
        protected=None,
        ci_status=deploy_ci,
    )

    if not token or not repo:
        reason = (
            "GITHUB_TOKEN/GITHUB_API_TOKEN and GITHUB_REPOSITORY are not configured"
        )
        logger.info("operations_github_unavailable", extra={"reason": reason})
        return GitHubOut(
            available=False,
            unavailable_reason=reason,
            repository=repo,
            latest_commits=[],
            open_pull_requests=[],
            failed_actions=[],
            branch_status=branch_fallback,
            generated_at=now,
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "lumora-operations-dashboard",
    }
    commits: list[GitHubCommit] = []
    prs: list[GitHubPullRequest] = []
    failed: list[GitHubActionRun] = []
    branch_status = branch_fallback

    try:
        async with httpx.AsyncClient(timeout=12.0, headers=headers) as client:
            branch_name = deploy_branch or "main"
            commits_resp = await client.get(
                f"{_API}/repos/{repo}/commits",
                params={"sha": branch_name, "per_page": 10},
            )
            if commits_resp.status_code >= 400:
                raise RuntimeError(
                    f"commits HTTP {commits_resp.status_code}: {commits_resp.text[:200]}"
                )
            for item in commits_resp.json():
                commit = item.get("commit") or {}
                author = (commit.get("author") or {}).get("name")
                commits.append(
                    GitHubCommit(
                        sha=item.get("sha") or "",
                        message=(commit.get("message") or "").split("\n", 1)[0],
                        author=author,
                        committed_at=_parse_dt((commit.get("author") or {}).get("date")),
                        url=item.get("html_url"),
                    )
                )

            prs_resp = await client.get(
                f"{_API}/repos/{repo}/pulls",
                params={"state": "open", "per_page": 20, "sort": "updated"},
            )
            if prs_resp.status_code >= 400:
                raise RuntimeError(
                    f"pulls HTTP {prs_resp.status_code}: {prs_resp.text[:200]}"
                )
            for item in prs_resp.json():
                prs.append(
                    GitHubPullRequest(
                        number=int(item["number"]),
                        title=item.get("title") or "",
                        state=item.get("state") or "open",
                        author=(item.get("user") or {}).get("login"),
                        updated_at=_parse_dt(item.get("updated_at")),
                        url=item.get("html_url"),
                    )
                )

            actions_resp = await client.get(
                f"{_API}/repos/{repo}/actions/runs",
                params={"status": "completed", "per_page": 30},
            )
            if actions_resp.status_code >= 400:
                raise RuntimeError(
                    f"actions HTTP {actions_resp.status_code}: {actions_resp.text[:200]}"
                )
            for item in (actions_resp.json() or {}).get("workflow_runs") or []:
                conclusion = item.get("conclusion")
                if conclusion not in {"failure", "timed_out", "cancelled"}:
                    continue
                failed.append(
                    GitHubActionRun(
                        id=int(item["id"]),
                        name=item.get("name") or item.get("display_title") or "workflow",
                        status=item.get("status") or "completed",
                        conclusion=conclusion,
                        branch=item.get("head_branch"),
                        updated_at=_parse_dt(item.get("updated_at")),
                        url=item.get("html_url"),
                    )
                )
                if len(failed) >= 10:
                    break

            branch_resp = await client.get(
                f"{_API}/repos/{repo}/branches/{branch_name}"
            )
            if branch_resp.status_code == 200:
                body = branch_resp.json()
                commit_sha = ((body.get("commit") or {}).get("sha")) or deploy_sha
                branch_status = GitHubBranchStatus(
                    name=body.get("name") or branch_name,
                    sha=commit_sha,
                    protected=body.get("protected"),
                    ci_status=deploy_ci,
                )
    except Exception as exc:
        logger.warning(
            "operations_github_fetch_failed",
            extra={"repository": repo, "error": str(exc)},
        )
        return GitHubOut(
            available=False,
            unavailable_reason=f"GitHub API unavailable: {exc}",
            repository=repo,
            latest_commits=[],
            open_pull_requests=[],
            failed_actions=[],
            branch_status=branch_fallback,
            generated_at=now,
        )

    return GitHubOut(
        available=True,
        unavailable_reason=None,
        repository=repo,
        latest_commits=commits,
        open_pull_requests=prs,
        failed_actions=failed,
        branch_status=branch_status,
        generated_at=now,
    )
