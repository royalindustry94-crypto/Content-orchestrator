#!/usr/bin/env python3
"""Validate repository agent skills, Cursor config, and executable entrypoints."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def error(message: str) -> None:
    ERRORS.append(message)


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        error(f"{path.relative_to(ROOT)}: missing YAML frontmatter")
        return {}
    raw = text.split("\n---\n", 1)[0][4:]
    values: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.startswith((" ", "\t")):
            continue
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip().strip('"')
    return values


def validate_skills() -> None:
    skill_root = ROOT / ".agents" / "skills"
    expected = {
        "agent-handoff",
        "browser-smoke",
        "milestone-audit",
        "milestone-plan",
        "release-gate",
        "safe-migration",
    }
    found = {path.name for path in skill_root.iterdir() if path.is_dir()}
    missing = expected - found
    if missing:
        error(f"required skills missing: {sorted(missing)}")
    for folder in sorted(skill_root.iterdir()):
        if not folder.is_dir():
            continue
        skill_file = folder / "SKILL.md"
        if not skill_file.is_file():
            error(f"{folder.relative_to(ROOT)}: missing SKILL.md")
            continue
        metadata = frontmatter(skill_file)
        if metadata.get("name") != folder.name:
            error(f"{skill_file.relative_to(ROOT)}: name must match folder")
        if len(metadata.get("description", "")) < 20:
            error(f"{skill_file.relative_to(ROOT)}: description is missing or too vague")
        if re.search(r"\b(?:TODO|TBD|FIXME)\b", skill_file.read_text(encoding="utf-8")):
            error(f"{skill_file.relative_to(ROOT)}: unfinished placeholder")


def validate_subagents() -> None:
    expected = {"migration-auditor.md", "release-verifier.md", "security-auditor.md"}
    agent_root = ROOT / ".cursor" / "agents"
    found = {path.name for path in agent_root.glob("*.md")}
    missing = expected - found
    if missing:
        error(f"required subagents missing: {sorted(missing)}")
    for path in agent_root.glob("*.md"):
        metadata = frontmatter(path)
        if metadata.get("name") != path.stem:
            error(f"{path.relative_to(ROOT)}: name must match filename")
        if metadata.get("readonly") != "true":
            error(f"{path.relative_to(ROOT)}: independent auditors must be read-only")
        if metadata.get("model") != "inherit":
            error(f"{path.relative_to(ROOT)}: model must remain portable via inherit")


def validate_rules() -> None:
    expected = {
        "api-security.mdc",
        "content-orchestrator.mdc",
        "migrations.mdc",
        "release-evidence.mdc",
        "web-quality.mdc",
    }
    rule_root = ROOT / ".cursor" / "rules"
    found = {path.name for path in rule_root.glob("*.mdc")}
    missing = expected - found
    if missing:
        error(f"required rules missing: {sorted(missing)}")
    for path in rule_root.glob("*.mdc"):
        metadata = frontmatter(path)
        if len(metadata.get("description", "")) < 20:
            error(f"{path.relative_to(ROOT)}: description is missing or too vague")
        if metadata.get("alwaysApply") not in {"true", "false"}:
            error(f"{path.relative_to(ROOT)}: alwaysApply must be true or false")


def validate_json_and_commands() -> None:
    hooks_path = ROOT / ".cursor" / "hooks.json"
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    if hooks.get("version") != 1:
        error(".cursor/hooks.json: version must be 1")
    for definitions in hooks.get("hooks", {}).values():
        for definition in definitions:
            command = definition.get("command", "")
            target = command.split()[-1]
            if not (ROOT / target).is_file():
                error(f".cursor/hooks.json: missing command target {target}")
            if definition.get("failClosed") is not True:
                error(f".cursor/hooks.json: safety hook must fail closed: {command}")

    environment_path = ROOT / ".cursor" / "environment.json"
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    allowed_environment_keys = {
        "agentCanUpdateSnapshot",
        "build",
        "chromeExecutablePath",
        "disableAllMcpServers",
        "egressAllowlist",
        "egressMode",
        "enable_testing",
        "image",
        "install",
        "mcpServerAllowlist",
        "name",
        "ports",
        "repositoryDependencies",
        "snapshot",
        "start",
        "terminals",
        "user",
    }
    unknown_environment_keys = set(environment) - allowed_environment_keys
    if unknown_environment_keys:
        error(f".cursor/environment.json: unknown keys {sorted(unknown_environment_keys)}")
    for key in ("install", "start"):
        if not isinstance(environment.get(key), str) or not environment[key].strip():
            error(f".cursor/environment.json: {key} must be a non-empty command")
            continue
        target = environment[key].split()[-1]
        if not (ROOT / target).is_file():
            error(f".cursor/environment.json: missing {key} target {target}")
    ports = environment.get("ports")
    if not isinstance(ports, list) or not ports:
        error(".cursor/environment.json: ports must be a non-empty array")
    elif any(
        not isinstance(port, dict)
        or not isinstance(port.get("port"), int)
        or not 1 <= port["port"] <= 65535
        for port in ports
    ):
        error(".cursor/environment.json: every port requires a valid integer port")
    terminals = environment.get("terminals")
    if not isinstance(terminals, list) or not terminals:
        error(".cursor/environment.json: terminals must be a non-empty array")
    elif any(
        not isinstance(terminal, dict)
        or not isinstance(terminal.get("command"), str)
        or not terminal["command"].strip()
        for terminal in terminals
    ):
        error(".cursor/environment.json: every terminal requires a command")

    schema_path = ROOT / ".agents" / "coordination" / "handoff.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if schema.get("properties", {}).get("schema_version", {}).get("const") != 1:
        error("handoff schema must pin schema_version 1")


def validate_entrypoints() -> None:
    for relative in (
        "scripts/agent-check.sh",
        "scripts/agent_handoff.py",
        "scripts/validate_agent_config.py",
        ".cursor/cloud/install.sh",
        ".cursor/cloud/start.sh",
        ".cursor/hooks/guard_shell.py",
        ".cursor/hooks/guard_read.py",
    ):
        path = ROOT / relative
        if not path.is_file():
            error(f"missing entrypoint: {relative}")
        elif not os.access(path, os.X_OK):
            error(f"entrypoint is not executable: {relative}")


def main() -> int:
    try:
        validate_skills()
        validate_subagents()
        validate_rules()
        validate_json_and_commands()
        validate_entrypoints()
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        error(f"validation crashed: {exc}")

    if ERRORS:
        for message in ERRORS:
            print(f"ERROR: {message}", file=sys.stderr)
        return 1
    print("Agent configuration validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
