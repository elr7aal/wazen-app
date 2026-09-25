"""Add idempotency records.

Revision ID: 0002_idempotency
Revises: 0001_current_schema
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_idempotency"
down_revision = "0001_current_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind=op.get_bind()
    inspector=sa.inspect(bind)
    if "idempotency_records" in inspector.get_table_names():
        return
    op.create_table(
        "idempotency_records",
        sa.Column("id",sa.String(length=36),primary_key=True),
        sa.Column("user_id",sa.String(length=36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("method",sa.String(length=12),nullable=False),
        sa.Column("path",sa.String(length=255),nullable=False),
        sa.Column("idempotency_key",sa.String(length=120),nullable=False),
        sa.Column("request_hash",sa.String(length=64),nullable=False),
        sa.Column("state",sa.String(length=20),nullable=False,server_default="PENDING"),
        sa.Column("response_json",sa.Text(),nullable=True),
        sa.Column("created_at",sa.DateTime(),nullable=False),
        sa.Column("completed_at",sa.DateTime(),nullable=True),
        sa.UniqueConstraint("user_id","method","path","idempotency_key",name="uq_idempotency_scope"),
    )
    op.create_index("ix_idempotency_records_user_id","idempotency_records",["user_id"])
    op.create_index("ix_idempotency_records_idempotency_key","idempotency_records",["idempotency_key"])
    op.create_index("ix_idempotency_records_state","idempotency_records",["state"])
    op.create_index("ix_idempotency_records_created_at","idempotency_records",["created_at"])


def downgrade() -> None:
    op.drop_table("idempotency_records")
