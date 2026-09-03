#!/usr/bin/env python3
"""Fail-closed guard for destructive shell commands issued by Cursor agents."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path


GIT = (
    r"\bgit(?:\s+(?:(?:-C|-c|--git-dir|--work-tree|--config-env)\s+\S+"
    r"|--(?:git-dir|work-tree)=\S+|--(?:no-)?pager))*\s+"
)
BLOCKED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "force-pushing is not allowed",
        re.compile(GIT + r"push\b[^\n]*(?:--force(?:-with-lease)?|\s-f(?:\s|$)|\s\+\S+)", re.I),
    ),
    (
        "direct pushes to main are not allowed",
        re.compile(GIT + r"push\b[^\n]*(?:\s|:)(?:refs/heads/)?main(?:\s|$)", re.I),
    ),
    ("hard resets are not allowed", re.compile(GIT + r"reset\b[^\n]*--hard\b", re.I)),
    ("forced git clean is not allowed", re.compile(GIT + r"clean\b[^\n]*(?:--force|-[a-z]*f)", re.I)),
    (
        "recursive forced deletion is not allowed",
        re.compile(
            r"\brm\b(?=[^\n]*(?:\s--recursive\b|\s-[a-z]*r[a-z]*\b))"
            r"(?=[^\n]*(?:\s--force\b|\s-[a-z]*f[a-z]*\b))",
            re.I,
        ),
    ),
    (
        "run migration replay through scripts/agent-check.sh full",
        re.compile(r"\balembic\b[^\n]*\bdowngrade\b", re.I),
    ),
)

RAW_DATABASE_CLIENT = re.compile(r"\b(?:psql|mysql|sqlite3)\b", re.I)
SENSITIVE_REFERENCE = re.compile(
    r"(?<![\w.-])(?:"
    r"\.env(?!\.example(?:\s|$|['\";|&]))(?:\.[\w.-]+)?"
    r"|\.envrc|\.netrc|\.git-credentials|\.pypirc"
    r"|(?:\.aws|gcloud)[/\\]credentials(?:\.json)?"
    r"|application_default_credentials\.json"
    r"|(?:id_rsa|id_ed25519)(?!\.pub\b)"
    r"|[^\s'\"]+\.(?:pem|key|p12|pfx)"
    r")",
    re.I,
)
PYTHON_DELETION = re.compile(r"\b(?:shutil\.rmtree|os\.remove|os\.unlink)\b", re.I)
FIND_DELETE = re.compile(r"\bfind\b[^\n]*(?:\s-delete\b|\s-exec\s+rm\b)", re.I)
SHELL_FILE_READER = re.compile(
    r"\b(?:cat|head|tail|less|more|sed|awk|grep|rg|strings|xxd|base64|source)\b",
    re.I,
)
HIDDEN_PATH_EXPANSION = re.compile(r"(?<!\w)\.[^\s'\"/]*[?*{][^\s'\"/]*")
CREDENTIAL_PATH_EXPANSION = re.compile(
    r"(?:^|[/~\s'\"=])(?:cred(?:ential)?s?|id_|\.env|\.e|\.netrc|\.git-credentials"
    r"|application_default)[^/\s'\";|&]*[?*{][^/\s'\";|&]*",
    re.I,
)
GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--config-env", "--git-dir", "--work-tree"}


def respond(permission: str, message: str | None = None) -> None:
    payload: dict[str, str] = {"permission": permission}
    if message:
        payload["user_message"] = message
        payload["agent_message"] = message
    print(json.dumps(payload))


def sensitive_staged_files() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    unsafe: list[str] = []
    for raw_path in result.stdout.splitlines():
        path = Path(raw_path)
        name = path.name.lower()
        if name == ".env.example":
            continue
        if (
            name == ".env"
            or name.startswith(".env.")
            or name == ".envrc"
            or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
        ):
            unsafe.append(raw_path)
        elif name in {
            ".git-credentials",
            ".netrc",
            "application_default_credentials.json",
            "credentials.json",
            "id_ed25519",
            "id_rsa",
            "secrets.json",
            "token.json",
        }:
            unsafe.append(raw_path)
    return unsafe


def git_operations(command: str) -> list[tuple[str, list[str]]]:
    """Extract common Git subcommands after global options without executing a shell."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return []
    operations: list[tuple[str, list[str]]] = []
    for index, token in enumerate(tokens):
        if Path(token).name != "git":
            continue
        cursor = index + 1
        while cursor < len(tokens):
            candidate = tokens[cursor]
            if candidate in GIT_OPTIONS_WITH_VALUE:
                cursor += 2
                continue
            if candidate.startswith(("-C", "-c")) and candidate not in {"-C", "-c"}:
                cursor += 1
                continue
            if candidate.startswith("-"):
                cursor += 1
                continue
            operations.append((candidate, tokens[cursor + 1 :]))
            break
    return operations


def blocked_git_operation(command: str) -> str | None:
    for operation, arguments in git_operations(command):
        if operation == "push":
            if any(
                argument in {"-f", "--force"}
                or argument.startswith("--force-with-lease")
                or argument.startswith("+")
                for argument in arguments
            ):
                return "force-pushing is not allowed"
            for argument in arguments:
                destination = argument.split(":", 1)[-1]
                if destination in {"main", "refs/heads/main"}:
                    return "direct pushes to main are not allowed"
        elif operation == "reset" and "--hard" in arguments:
            return "hard resets are not allowed"
        elif operation == "clean" and any(
            argument == "--force"
            or (argument.startswith("-") and not argument.startswith("--") and "f" in argument)
            for argument in arguments
        ):
            return "forced git clean is not allowed"
    return None


def main() -> int:
    try:
        request = json.load(sys.stdin)
        command = request.get("command")
        if not isinstance(command, str):
            raise ValueError("missing command")
    except (json.JSONDecodeError, ValueError, AttributeError) as exc:
        respond("deny", f"Shell guard could not validate the command: {exc}")
        return 2

    git_reason = blocked_git_operation(command)
    if git_reason:
        respond("deny", f"Blocked by repository safety policy: {git_reason}.")
        return 2

    for reason, pattern in BLOCKED_PATTERNS:
        if pattern.search(command):
            respond("deny", f"Blocked by repository safety policy: {reason}.")
            return 2

    if SENSITIVE_REFERENCE.search(command):
        respond("deny", "Blocked shell access to a local credential file.")
        return 2

    if SHELL_FILE_READER.search(command) and (
        HIDDEN_PATH_EXPANSION.search(command) or CREDENTIAL_PATH_EXPANSION.search(command)
    ):
        respond("deny", "Blocked wildcard or brace expansion over hidden files.")
        return 2

    if RAW_DATABASE_CLIENT.search(command):
        respond(
            "deny",
            "Blocked direct raw database client use; use application tests or the guarded evidence runner.",
        )
        return 2

    if PYTHON_DELETION.search(command) or FIND_DELETE.search(command):
        respond("deny", "Blocked a high-risk recursive or scripted deletion command.")
        return 2

    if any(operation == "commit" for operation, _ in git_operations(command)):
        unsafe = sensitive_staged_files()
        if unsafe:
            respond("deny", "Blocked commit containing sensitive file names: " + ", ".join(unsafe))
            return 2

    respond("allow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
