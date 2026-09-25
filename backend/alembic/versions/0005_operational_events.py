"""Add operational events.

Revision ID: 0005_operational_events
Revises: 0004_security_events
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_operational_events"
down_revision = "0004_security_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind=op.get_bind()
    inspector=sa.inspect(bind)
    if "operational_events" in inspector.get_table_names():
        return
    op.create_table(
        "operational_events",
        sa.Column("id",sa.String(length=36),primary_key=True),
        sa.Column("event_type",sa.String(length=32),nullable=False),
        sa.Column("method",sa.String(length=12),nullable=False),
        sa.Column("path",sa.String(length=255),nullable=False),
        sa.Column("status_code",sa.Integer(),nullable=False),
        sa.Column("duration_ms",sa.Float(),nullable=False),
        sa.Column("request_id",sa.String(length=80),nullable=True),
        sa.Column("details_json",sa.Text(),nullable=False,server_default="{}"),
        sa.Column("created_at",sa.DateTime(),nullable=False),
    )
    for name,column in [
        ("ix_operational_events_event_type","event_type"),
        ("ix_operational_events_path","path"),
        ("ix_operational_events_status_code","status_code"),
        ("ix_operational_events_request_id","request_id"),
        ("ix_operational_events_created_at","created_at"),
    ]:
        op.create_index(name,"operational_events",[column])


def downgrade() -> None:
    op.drop_table("operational_events")
