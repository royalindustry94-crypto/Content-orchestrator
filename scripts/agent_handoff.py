#!/usr/bin/env python3
"""Create and validate structured handoffs between repository-aware agents."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"in_progress", "ready_for_review", "changes_requested", "blocked", "verified", "failed"}
RESULTS = {"PASS", "FAIL", "NOT-RUN"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def safe_id(value: str) -> str:
    cleaned = SAFE_ID_RE.sub("-", value).strip("-.")
    if not cleaned:
        raise ValueError("task and agent identifiers must contain letters or numbers")
    return cleaned[:100]


def parse_check(raw: str) -> dict[str, str]:
    parts = raw.split("|", 2)
    if len(parts) != 3 or parts[1] not in RESULTS:
        raise argparse.ArgumentTypeError("checks use NAME|PASS|EVIDENCE, NAME|FAIL|EVIDENCE, or NAME|NOT-RUN|EVIDENCE")
    return {"name": parts[0].strip(), "result": parts[1], "evidence": parts[2].strip()}


def validate_payload(payload: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["handoff must be a JSON object"]
    required = {
        "schema_version", "task_id", "from_agent", "to_agent", "status", "branch",
        "head_sha", "tree_sha", "base_sha", "worktree_clean", "created_at", "summary",
        "checks", "blockers", "next_actions",
    }
    missing = required - payload.keys()
    extra = payload.keys() - required
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
    if extra:
        errors.append(f"unexpected fields: {sorted(extra)}")
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if payload.get("status") not in STATUSES:
        errors.append(f"invalid status: {payload.get('status')}")
    for field in ("task_id", "from_agent", "to_agent", "branch", "summary"):
        if not isinstance(payload.get(field), str) or not payload.get(field, "").strip():
            errors.append(f"{field} must be a non-empty string")
    for field in ("task_id", "from_agent", "to_agent"):
        if isinstance(payload.get(field), str) and len(payload[field]) > 100:
            errors.append(f"{field} must not exceed 100 characters")
    for field in ("head_sha", "tree_sha", "base_sha"):
        if not isinstance(payload.get(field), str) or not SHA_RE.fullmatch(payload.get(field, "")):
            errors.append(f"{field} must be a full lowercase Git SHA")
    if not isinstance(payload.get("worktree_clean"), bool):
        errors.append("worktree_clean must be a boolean")
    for field in ("checks", "blockers", "next_actions"):
        if not isinstance(payload.get(field), list):
            errors.append(f"{field} must be an array")
    for check in payload.get("checks", []) if isinstance(payload.get("checks"), list) else []:
        if not isinstance(check, dict) or set(check) != {"name", "result", "evidence"}:
            errors.append("every check requires only name, result, and evidence")
        elif check.get("result") not in RESULTS:
            errors.append(f"invalid check result: {check.get('result')}")
        elif not isinstance(check.get("name"), str) or not check["name"].strip():
            errors.append("every check name must be a non-empty string")
        elif not isinstance(check.get("evidence"), str) or not check["evidence"].strip():
            errors.append("every check evidence must be a non-empty string")
    for field in ("blockers", "next_actions"):
        values = payload.get(field)
        if isinstance(values, list) and any(
            not isinstance(value, str) or not value.strip() for value in values
        ):
            errors.append(f"every {field} item must be a non-empty string")
    checks = payload.get("checks")
    blockers = payload.get("blockers")
    next_actions = payload.get("next_actions")
    if payload.get("status") == "verified":
        if not isinstance(checks, list) or not checks:
            errors.append("verified handoffs require at least one check")
        elif any(isinstance(check, dict) and check.get("result") != "PASS" for check in checks):
            errors.append("verified handoffs may contain only PASS checks")
        if isinstance(blockers, list) and blockers:
            errors.append("verified handoffs cannot contain blockers")
    if payload.get("status") in {"ready_for_review", "verified"} and payload.get("worktree_clean") is not True:
        errors.append(f"{payload.get('status')} handoffs require a clean worktree")
    if payload.get("status") in {"blocked", "failed"} and isinstance(blockers, list) and not blockers:
        errors.append(f"{payload.get('status')} handoffs require at least one blocker")
    if payload.get("status") == "ready_for_review" and isinstance(next_actions, list) and not next_actions:
        errors.append("ready_for_review handoffs require at least one next action")
    try:
        created_at = datetime.fromisoformat(
            str(payload.get("created_at", "")).replace("Z", "+00:00")
        )
        if created_at.tzinfo is None:
            errors.append("created_at must include a timezone")
    except ValueError:
        errors.append("created_at must be an ISO-8601 timestamp")
    return errors


def create(args: argparse.Namespace) -> int:
    branch = git("branch", "--show-current") or "DETACHED"
    head_sha = git("rev-parse", "HEAD")
    tree_sha = git("rev-parse", "HEAD^{tree}")
    base_sha = args.base_sha or git("merge-base", "HEAD", "origin/main")
    worktree_clean = not bool(git("status", "--porcelain=v1"))
    timestamp = datetime.now(UTC)
    payload = {
        "schema_version": 1,
        "task_id": args.task_id,
        "from_agent": args.from_agent,
        "to_agent": args.to_agent,
        "status": args.status,
        "branch": branch,
        "head_sha": head_sha,
        "tree_sha": tree_sha,
        "base_sha": base_sha,
        "worktree_clean": worktree_clean,
        "created_at": timestamp.isoformat().replace("+00:00", "Z"),
        "summary": args.summary,
        "checks": args.check,
        "blockers": args.blocker,
        "next_actions": args.next_action,
    }
    errors = validate_payload(payload)
    if branch == "DETACHED" and args.status in {"ready_for_review", "verified"}:
        errors.append(f"{args.status} handoffs require a named branch")
    if errors:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        return 1

    task = safe_id(args.task_id)
    sender = safe_id(args.from_agent)
    base_dir = ROOT / (".agents/handoffs" if args.publish else "validation-logs/agent-handoffs") / task
    base_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}-{sender}.json"
    output = base_dir / filename
    with output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")
    print(output.relative_to(ROOT))
    return 0


def validate_repository_refs(payload: dict[str, object], path: Path) -> list[str]:
    errors: list[str] = []
    for field in ("head_sha", "base_sha"):
        try:
            git("cat-file", "-e", f"{payload[field]}^{{commit}}")
        except subprocess.CalledProcessError:
            errors.append(f"{field} is not present in this repository clone")
    if errors:
        return errors

    actual_tree = git("rev-parse", f"{payload['head_sha']}^{{tree}}")
    if actual_tree != payload["tree_sha"]:
        errors.append("tree_sha does not match head_sha")

    base_is_ancestor = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "merge-base",
            "--is-ancestor",
            str(payload["base_sha"]),
            str(payload["head_sha"]),
        ],
        check=False,
        capture_output=True,
        timeout=5,
    ).returncode == 0
    if not base_is_ancestor:
        errors.append("base_sha is not an ancestor of head_sha")

    branch_found = False
    branch_contains_head = False
    for branch_ref in (str(payload["branch"]), f"origin/{payload['branch']}"):
        exists = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", branch_ref],
            check=False,
            capture_output=True,
            timeout=5,
        ).returncode == 0
        if not exists:
            continue
        branch_found = True
        if subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "merge-base",
                "--is-ancestor",
                str(payload["head_sha"]),
                branch_ref,
            ],
            check=False,
            capture_output=True,
            timeout=5,
        ).returncode == 0:
            branch_contains_head = True
            break
    if not branch_found:
        errors.append("recorded branch is not present in this clone")
    elif not branch_contains_head:
        errors.append("recorded branch does not contain head_sha")

    expected_task_folder = safe_id(str(payload["task_id"]))
    if path.parent.name != expected_task_folder:
        errors.append("handoff parent folder does not match task_id")
    return errors


def validate(args: argparse.Namespace) -> int:
    path = Path(args.path).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_payload(payload)
    if not errors and isinstance(payload, dict):
        errors.extend(validate_repository_refs(payload, path))
    if errors:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        return 1
    print(f"Valid handoff: {path}")
    return 0


def validate_all(args: argparse.Namespace) -> int:
    handoff_root = ROOT / ".agents" / "handoffs"
    paths = sorted(handoff_root.glob("**/*.json"))
    if not paths:
        print("No published handoffs to validate")
        return 0
    failed = False
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_payload(payload)
        if args.require_commits and not errors and isinstance(payload, dict):
            errors.extend(validate_repository_refs(payload, path))
        if errors:
            failed = True
            for message in errors:
                print(f"ERROR: {path.relative_to(ROOT)}: {message}", file=sys.stderr)
        else:
            print(f"Valid handoff: {path.relative_to(ROOT)}")
    return 1 if failed else 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    create_parser = commands.add_parser("create", help="create a handoff")
    create_parser.add_argument("--task-id", required=True)
    create_parser.add_argument("--from-agent", required=True)
    create_parser.add_argument("--to-agent", required=True)
    create_parser.add_argument("--status", choices=sorted(STATUSES), required=True)
    create_parser.add_argument("--summary", required=True)
    create_parser.add_argument("--base-sha")
    create_parser.add_argument("--check", action="append", default=[], type=parse_check)
    create_parser.add_argument("--blocker", action="append", default=[])
    create_parser.add_argument("--next-action", action="append", default=[])
    create_parser.add_argument("--publish", action="store_true")
    create_parser.set_defaults(handler=create)
    validate_parser = commands.add_parser("validate", help="validate a handoff")
    validate_parser.add_argument("path")
    validate_parser.set_defaults(handler=validate)
    validate_all_parser = commands.add_parser(
        "validate-all", help="validate all handoffs published in the repository"
    )
    validate_all_parser.add_argument(
        "--require-commits",
        action="store_true",
        help="also require every referenced commit to exist in this clone",
    )
    validate_all_parser.set_defaults(handler=validate_all)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.handler(args)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
