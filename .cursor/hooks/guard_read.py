#!/usr/bin/env python3
"""Prevent Cursor agents from reading common local credential files."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    try:
        request = json.load(sys.stdin)
        file_path = request.get("file_path")
        if not isinstance(file_path, str):
            raise ValueError("missing file_path")
    except (json.JSONDecodeError, ValueError, AttributeError) as exc:
        message = f"File-read guard could not validate the request: {exc}"
        print(json.dumps({"permission": "deny", "user_message": message}))
        return 2

    path = Path(file_path)
    name = path.name.lower()
    credential_names = {
        ".netrc",
        ".git-credentials",
        ".pypirc",
        "application_default_credentials.json",
        "authorized_user.json",
        "credentials.json",
        "id_rsa",
        "id_ed25519",
        "secrets.json",
        "service-account.json",
        "token.json",
    }
    lower_parts = tuple(part.lower() for part in path.parts)
    sensitive = any(
        (
            (name == ".env" or name.startswith(".env.")) and name != ".env.example",
            name == ".envrc",
            path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"},
            name in credential_names,
            name == "credentials"
            and any(part in {".aws", ".config", "gcloud"} for part in lower_parts),
        )
    )

    if sensitive:
        message = f"Blocked agent read of local credential file: {path.name}"
        print(json.dumps({"permission": "deny", "user_message": message}))
        return 2

    print(json.dumps({"permission": "allow"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
