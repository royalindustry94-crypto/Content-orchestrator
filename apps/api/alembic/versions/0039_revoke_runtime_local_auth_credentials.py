"""Remove runtime-role access to local authentication credential hashes.

The local-auth credential table has no workspace identifier and must be read
before a caller is authenticated.  It is therefore intentionally serviced only
by the owner-role authentication endpoints, not by the RLS-bound `app_runtime`
connection used for authenticated product requests.

The previous migration granted SELECT, INSERT and UPDATE on this table to
`app_runtime`.  Direct verification proved that the runtime role could query
credential rows, including password hashes, despite no runtime application path
requiring that grant.  This migration removes the excess privilege without
changing local-auth endpoint behavior or weakening password/lockout controls.

Revision ID: 0039
Revises: 0038
"""

from __future__ import annotations

from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("REVOKE ALL PRIVILEGES ON TABLE local_auth_credentials FROM app_runtime;")


def downgrade() -> None:
    # Restores the exact historical grant surface for a controlled downgrade.
    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE local_auth_credentials TO app_runtime;")
