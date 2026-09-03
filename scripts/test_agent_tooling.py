#!/usr/bin/env python3
"""Regression tests for repository agent guards and handoff validation."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_guard(relative: str, payload: dict[str, str]) -> tuple[int, dict[str, str]]:
    result = subprocess.run(
        [sys.executable, str(ROOT / relative)],
        input=json.dumps(payload),
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    return result.returncode, json.loads(result.stdout)


class ShellGuardTests(unittest.TestCase):
    def assert_denied(self, command: str) -> None:
        returncode, payload = run_guard(
            ".cursor/hooks/guard_shell.py", {"command": command}
        )
        self.assertEqual(returncode, 2, command)
        self.assertEqual(payload["permission"], "deny", command)

    def test_allows_normal_development_commands(self) -> None:
        for command in ("git status --short", "pytest -q", "git push origin feature/agent"):
            with self.subTest(command=command):
                returncode, payload = run_guard(
                    ".cursor/hooks/guard_shell.py", {"command": command}
                )
                self.assertEqual(returncode, 0)
                self.assertEqual(payload, {"permission": "allow"})

    def test_blocks_destructive_and_protected_commands(self) -> None:
        commands = (
            "git push origin main",
            "git -C . push origin HEAD:refs/heads/main",
            "git -C. push origin main",
            "git --literal-pathspecs push origin main",
            "git --bare push origin main",
            "git -cfoo.bar=baz push origin main",
            "git -c advice.detachedHead=false push origin +feature",
            "git push --force-with-lease origin feature",
            "git -C . reset --hard HEAD",
            "git clean -fdx",
            "rm -r -f build",
            "rm --recursive --force build",
            "alembic -x tenant=demo downgrade base",
            "psql -c 'DROP TABLE customers'",
            "echo 'DELETE FROM customers' | psql database",
            "psql -c 'SELECT 1'",
            "psql -f destructive.sql",
            "python -c 'import shutil; shutil.rmtree(\"build\")'",
            "find build -delete",
            "cat .env",
            "python -c \"open('.aws/credentials').read()\"",
            "cp private/client.key /tmp/client.key",
            "cat .e??",
            "head .{env,netrc}",
            "cat .aws/cred*",
            "cat ~/.aws/cred*",
            "cat id_*",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_fails_closed_on_invalid_input(self) -> None:
        returncode, payload = run_guard(".cursor/hooks/guard_shell.py", {})
        self.assertEqual(returncode, 2)
        self.assertEqual(payload["permission"], "deny")


class ReadGuardTests(unittest.TestCase):
    def test_allows_source_and_example_environment(self) -> None:
        for file_path in ("apps/api/app/main.py", ".env.example"):
            with self.subTest(file_path=file_path):
                returncode, payload = run_guard(
                    ".cursor/hooks/guard_read.py", {"file_path": file_path}
                )
                self.assertEqual(returncode, 0)
                self.assertEqual(payload, {"permission": "allow"})

    def test_blocks_common_credential_files(self) -> None:
        paths = (
            ".env",
            ".env.local",
            ".envrc",
            ".netrc",
            ".git-credentials",
            ".aws/credentials",
            ".config/gcloud/application_default_credentials.json",
            "private/id_ed25519",
            "private/client.key",
        )
        for file_path in paths:
            with self.subTest(file_path=file_path):
                returncode, payload = run_guard(
                    ".cursor/hooks/guard_read.py", {"file_path": file_path}
                )
                self.assertEqual(returncode, 2)
                self.assertEqual(payload["permission"], "deny")


class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module("agent_handoff", "scripts/agent_handoff.py")

    def payload(self) -> dict[str, object]:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=ROOT,
        ).stdout.strip()
        return {
            "schema_version": 1,
            "task_id": "reliability-foundation",
            "from_agent": "codex-builder",
            "to_agent": "cursor-release-verifier",
            "status": "ready_for_review",
            "branch": "cursor/agent-reliability-foundation",
            "head_sha": head,
            "tree_sha": subprocess.run(
                ["git", "rev-parse", "HEAD^{tree}"],
                check=True,
                capture_output=True,
                text=True,
                cwd=ROOT,
            ).stdout.strip(),
            "base_sha": head,
            "worktree_clean": True,
            "created_at": datetime.now(UTC).isoformat(),
            "summary": "Ready for an independent exact-head review.",
            "checks": [
                {"name": "tooling tests", "result": "PASS", "evidence": "local unittest"}
            ],
            "blockers": [],
            "next_actions": ["Audit without editing the branch."],
        }

    def test_valid_payload(self) -> None:
        self.assertEqual(self.module.validate_payload(self.payload()), [])

    def test_rejects_false_result_and_extra_field(self) -> None:
        payload = self.payload()
        payload["checks"][0]["result"] = "SUCCESS"  # type: ignore[index]
        payload["unverified_claim"] = True
        errors = self.module.validate_payload(payload)
        self.assertTrue(any("unexpected fields" in error for error in errors))
        self.assertTrue(any("invalid check result" in error for error in errors))

    def test_verified_requires_only_passes_and_no_blockers(self) -> None:
        payload = self.payload()
        payload["status"] = "verified"
        payload["checks"][0]["result"] = "NOT-RUN"  # type: ignore[index]
        payload["blockers"] = ["Hosted CI did not run."]
        errors = self.module.validate_payload(payload)
        self.assertTrue(any("only PASS" in error for error in errors))
        self.assertTrue(any("cannot contain blockers" in error for error in errors))

    def test_ready_for_review_requires_clean_worktree(self) -> None:
        payload = self.payload()
        payload["worktree_clean"] = False
        errors = self.module.validate_payload(payload)
        self.assertTrue(any("require a clean worktree" in error for error in errors))

    def test_verified_requires_non_empty_evidence(self) -> None:
        payload = self.payload()
        payload["status"] = "verified"
        payload["checks"][0]["evidence"] = "   "  # type: ignore[index]
        errors = self.module.validate_payload(payload)
        self.assertTrue(any("evidence must be a non-empty string" in error for error in errors))


class CloudEnvironmentTests(unittest.TestCase):
    def test_generated_cors_value_survives_shell_and_settings_parsing(self) -> None:
        install_script = (ROOT / ".cursor/cloud/install.sh").read_text(encoding="utf-8")
        cors_command = next(
            line.strip()
            for line in install_script.splitlines()
            if line.strip().startswith('printf "CORS_ALLOW_ORIGINS=')
        )
        rendered = subprocess.run(
            ["bash", "-c", cors_command],
            check=True,
            capture_output=True,
            text=True,
            cwd=ROOT,
        ).stdout
        with tempfile.TemporaryDirectory() as temporary_directory:
            environment_file = Path(temporary_directory) / "generated.env"
            environment_file.write_text(rendered, encoding="utf-8")
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    "set -a; source \"$1\"; set +a; "
                    "export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/content_orchestrator; "
                    "export APP_DATABASE_URL=postgresql://app_runtime:app_runtime@localhost:5432/content_orchestrator; "
                    "export SUPABASE_JWT_SECRET=agent-cors-test-secret-with-more-than-32-chars; "
                    "PYTHONPATH=apps/api \"$2\" -c 'from app.core.config import Settings; "
                    "print(\"|\".join(Settings().cors_allow_origins))'",
                    "agent-cors-test",
                    str(environment_file),
                    sys.executable,
                ],
                check=True,
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=10,
            )
        self.assertEqual(
            result.stdout.strip(),
            "http://localhost:5173|http://127.0.0.1:5173",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
