"""Add persistent auth rate limits.

Revision ID: 0003_auth_rate_limits
Revises: 0002_idempotency
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_auth_rate_limits"
down_revision = "0002_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind=op.get_bind()
    inspector=sa.inspect(bind)
    if "auth_rate_limits" in inspector.get_table_names():
        return
    op.create_table(
        "auth_rate_limits",
        sa.Column("id",sa.String(length=36),primary_key=True),
        sa.Column("scope",sa.String(length=32),nullable=False),
        sa.Column("subject_hash",sa.String(length=64),nullable=False),
        sa.Column("attempts",sa.Integer(),nullable=False,server_default="0"),
        sa.Column("window_started_at",sa.DateTime(),nullable=False),
        sa.Column("blocked_until",sa.DateTime(),nullable=True),
        sa.Column("updated_at",sa.DateTime(),nullable=False),
        sa.UniqueConstraint("scope","subject_hash",name="uq_auth_rate_limit_scope_subject"),
    )
    op.create_index("ix_auth_rate_limits_scope","auth_rate_limits",["scope"])
    op.create_index("ix_auth_rate_limits_subject_hash","auth_rate_limits",["subject_hash"])
    op.create_index("ix_auth_rate_limits_blocked_until","auth_rate_limits",["blocked_until"])


def downgrade() -> None:
    op.drop_table("auth_rate_limits")
