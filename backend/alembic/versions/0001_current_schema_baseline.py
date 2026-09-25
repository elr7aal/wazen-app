"""Reconcile current WAZEN schema baseline.

Revision ID: 0001_current_schema
Revises:
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

from app.db import Base
from app.models import db_models  # noqa: F401

revision = "0001_current_schema"
down_revision = None
branch_labels = None
depends_on = None


def _column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {x["name"] for x in inspector.get_columns(table_name)}


def _add_column_if_missing(bind, table_name: str, column: sa.Column) -> None:
    if column.name not in _column_names(bind, table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()

    # Create any table that does not exist yet. Existing tables are left intact.
    Base.metadata.create_all(bind=bind)

    # Reconcile known additive columns introduced during Alpha development.
    # These checks make this baseline safe both for a fresh database and an
    # older Alpha database that already contains the core tables.
    _add_column_if_missing(
        bind,
        "user_profiles",
        sa.Column("target_fiber_g", sa.Float(), nullable=True, server_default="30"),
    )
    _add_column_if_missing(
        bind,
        "user_profiles",
        sa.Column("condition_context_csv", sa.Text(), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        bind,
        "food_logs",
        sa.Column("fiber_g", sa.Float(), nullable=False, server_default="0"),
    )
    _add_column_if_missing(
        bind,
        "favorite_meals",
        sa.Column("fiber_g", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    # This is a reconciliation/baseline migration. Downgrade is intentionally
    # non-destructive so an existing Alpha database cannot be dropped by mistake.
    pass
