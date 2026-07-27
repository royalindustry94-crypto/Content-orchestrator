"""Reusable SQL emitters shared across Milestone 3 migrations.

Not application code — these assemble DDL strings that migrations pass to
op.execute(), keeping RLS/trigger/index boilerplate identical across every
table instead of copy-pasted and drifting.
"""

from __future__ import annotations

from alembic import op


def attach_version_trigger(table: str) -> None:
    op.execute(
        f"CREATE TRIGGER trg_{table}_version BEFORE UPDATE ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();"
    )


def attach_immutable_trigger(table: str) -> None:
    op.execute(
        f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION prevent_update();"
    )


def attach_immutable_delete_trigger(table: str) -> None:
    """Block DELETE as well as UPDATE — full append-only (WS3 audit tables)."""
    op.execute(
        f"CREATE TRIGGER trg_{table}_immutable_delete BEFORE DELETE ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )


def enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")


def grant_runtime(
    table: str, *, insert: bool = True, update: bool = True, delete: bool = True
) -> None:
    verbs = ["SELECT"]
    if insert:
        verbs.append("INSERT")
    if update:
        verbs.append("UPDATE")
    if delete:
        verbs.append("DELETE")
    op.execute(f"GRANT {', '.join(verbs)} ON {table} TO app_runtime;")


def _roles_array(roles: list[str]) -> str:
    joined = ",".join(f"'{r}'" for r in roles)
    return f"ARRAY[{joined}]::workspace_role[]"


def policy_select_members(table: str, roles: list[str], *, soft_delete: bool = False,
                          policy_suffix: str = "select_member") -> None:
    deleted_clause = "deleted_at IS NULL AND " if soft_delete else ""
    op.execute(
        f"CREATE POLICY {table}_{policy_suffix} ON {table} FOR SELECT "
        f"USING ({deleted_clause}app_user_has_workspace_role(workspace_id, {_roles_array(roles)}));"
    )


def policy_insert_roles(
    table: str, roles: list[str], *, policy_suffix: str = "insert_roles"
) -> None:
    op.execute(
        f"CREATE POLICY {table}_{policy_suffix} ON {table} FOR INSERT "
        f"WITH CHECK (app_user_has_workspace_role(workspace_id, {_roles_array(roles)}));"
    )


def policy_update_roles(
    table: str, roles: list[str], *, policy_suffix: str = "update_roles"
) -> None:
    op.execute(
        f"CREATE POLICY {table}_{policy_suffix} ON {table} FOR UPDATE "
        f"USING (app_user_has_workspace_role(workspace_id, {_roles_array(roles)}));"
    )


def policy_all_roles(table: str, roles: list[str], *, policy_suffix: str = "all_roles") -> None:
    op.execute(
        f"CREATE POLICY {table}_{policy_suffix} ON {table} FOR ALL "
        f"USING (app_user_has_workspace_role(workspace_id, {_roles_array(roles)}));"
    )
