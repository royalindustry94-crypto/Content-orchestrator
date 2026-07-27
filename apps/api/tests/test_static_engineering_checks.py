"""Static engineering checks that do not require a live database."""

from __future__ import annotations

import ast
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
VERSIONS = API_ROOT / "alembic" / "versions"
APP = API_ROOT / "app"


def _is_docstring(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def test_every_alembic_revision_defines_downgrade():
    files = sorted(VERSIONS.glob("*.py"))
    assert files, "no alembic versions found"
    missing = []
    trivial = []
    for path in files:
        tree = ast.parse(path.read_text(), filename=str(path))
        fn = next(
            (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "downgrade"),
            None,
        )
        if fn is None:
            missing.append(path.name)
            continue
        stmts = list(fn.body)
        if stmts and _is_docstring(stmts[0]):
            stmts = stmts[1:]
        if not stmts or all(isinstance(s, ast.Pass) for s in stmts):
            trivial.append(path.name)
    assert not missing, f"migrations missing downgrade(): {missing}"
    assert not trivial, f"migrations with empty downgrade(): {trivial}"


def test_no_bare_except_in_app():
    bare = []
    for path in APP.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                bare.append(f"{path.relative_to(API_ROOT)}:{node.lineno}")
    assert not bare, f"bare except: found (silent failure risk): {bare}"


def test_workspace_scoped_mixin_requires_workspace_id():
    text = (API_ROOT / "app" / "db" / "base.py").read_text()
    assert "class WorkspaceScopedMixin" in text
    assert "workspace_id" in text
    assert "nullable=False" in text
