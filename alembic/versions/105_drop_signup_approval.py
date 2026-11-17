"""Drop signup approval. Active accounts can use the app immediately.

Previously rejected signups stay locked out by deactivating the account.
Pending signups were already active and can sign in. Access keys existed
only to bypass the queue, so that table goes away. Session cutoff
(sessions_valid_after) stays: password resets still use it.

Revision ID: 105_drop_signup_approval
Revises: 104_user_profile_photo
Create Date: 2026-11-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "105_drop_signup_approval"
down_revision = "104_user_profile_photo"
branch_labels = None
depends_on = None

_APPROVAL_COLUMNS = ("approved_by", "approved_at", "approval_status")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" in tables:
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "approval_status" in cols:
            op.execute(sa.text("UPDATE users SET is_active = false WHERE approval_status = 'rejected'"))
        indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        if "ix_users_approval_status" in indexes:
            op.drop_index("ix_users_approval_status", table_name="users")
        for name in _APPROVAL_COLUMNS:
            if name in cols:
                op.drop_column("users", name)

    if "signup_access_keys" in tables:
        op.drop_table("signup_access_keys")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    cols = {c["name"] for c in inspector.get_columns("users")} if "users" in tables else set()

    if "approval_status" not in cols:
        op.add_column(
            "users",
            sa.Column("approval_status", sa.String(16), nullable=False, server_default="approved"),
        )
    if "approved_at" not in cols:
        op.add_column("users", sa.Column("approved_at", sa.DateTime(), nullable=True))
    if "approved_by" not in cols:
        op.add_column("users", sa.Column("approved_by", sa.String(36), nullable=True))

    indexes = {idx["name"] for idx in inspector.get_indexes("users")} if "users" in tables else set()
    if "ix_users_approval_status" not in indexes:
        op.create_index("ix_users_approval_status", "users", ["approval_status"])

    if "signup_access_keys" not in tables:
        op.create_table(
            "signup_access_keys",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_signup_access_keys_user_id", "signup_access_keys", ["user_id"])
