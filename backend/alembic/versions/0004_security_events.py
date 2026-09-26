"""Add security event audit.

Revision ID: 0004_security_events
Revises: 0003_auth_rate_limits
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_security_events"
down_revision = "0003_auth_rate_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind=op.get_bind()
    inspector=sa.inspect(bind)
    if "security_events" in inspector.get_table_names():
        return
    op.create_table(
        "security_events",
        sa.Column("id",sa.String(length=36),primary_key=True),
        sa.Column("event_type",sa.String(length=50),nullable=False),
        sa.Column("outcome",sa.String(length=24),nullable=False),
        sa.Column("user_id",sa.String(length=36),sa.ForeignKey("users.id"),nullable=True),
        sa.Column("subject_hash",sa.String(length=64),nullable=True),
        sa.Column("client_hash",sa.String(length=64),nullable=True),
        sa.Column("request_id",sa.String(length=80),nullable=True),
        sa.Column("details_json",sa.Text(),nullable=False,server_default="{}"),
        sa.Column("created_at",sa.DateTime(),nullable=False),
    )
    for name,column in [
        ("ix_security_events_event_type","event_type"),
        ("ix_security_events_outcome","outcome"),
        ("ix_security_events_user_id","user_id"),
        ("ix_security_events_subject_hash","subject_hash"),
        ("ix_security_events_client_hash","client_hash"),
        ("ix_security_events_request_id","request_id"),
        ("ix_security_events_created_at","created_at"),
    ]:
        op.create_index(name,"security_events",[column])


def downgrade() -> None:
    op.drop_table("security_events")
