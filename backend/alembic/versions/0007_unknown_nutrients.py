"""Preserve unknown fiber and sodium in saved meals."""
from alembic import op
import sqlalchemy as sa
revision = '0007_unknown_nutrients'
down_revision = '0006_email_verification'
branch_labels = None
depends_on = None


def upgrade():
    for table in ('food_logs', 'favorite_meals'):
        with op.batch_alter_table(table) as batch:
            for column in ('fiber_g', 'sodium_mg'):
                batch.alter_column(column, existing_type=sa.Float(), nullable=True, server_default=None)
        # Old releases stored missing values as zero; their provenance is lost.
        # Conservatively mark historical zeros unknown, retaining positive values.
        for column in ('fiber_g', 'sodium_mg'):
            op.execute(sa.text(f'UPDATE {table} SET {column} = NULL WHERE {column} = 0'))


def downgrade():
    for table in ('food_logs', 'favorite_meals'):
        for column in ('fiber_g', 'sodium_mg'):
            op.execute(sa.text(f'UPDATE {table} SET {column} = 0 WHERE {column} IS NULL'))
        with op.batch_alter_table(table) as batch:
            for column in ('fiber_g', 'sodium_mg'):
                batch.alter_column(column, existing_type=sa.Float(), nullable=False)
