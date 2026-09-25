"""Add email verification.

Revision ID: 0006_email_verification
Revises: 0005_operational_events
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_email_verification"
down_revision = "0005_operational_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind=op.get_bind()
    inspector=sa.inspect(bind)
    columns={c['name'] for c in inspector.get_columns('users')}
    with op.batch_alter_table('users') as batch:
        if 'email_verified' not in columns:
            batch.add_column(sa.Column('email_verified',sa.Boolean(),nullable=False,server_default=sa.false()))
        if 'email_verified_at' not in columns:
            batch.add_column(sa.Column('email_verified_at',sa.DateTime(),nullable=True))
    # Existing pre-v64 accounts are grandfathered as verified so the upgrade does not lock out Alpha users.
    bind.execute(sa.text("UPDATE users SET email_verified = 1 WHERE email_verified = 0"))

    inspector=sa.inspect(bind)
    indexes={i['name'] for i in inspector.get_indexes('users')}
    if 'ix_users_email_verified' not in indexes:
        op.create_index('ix_users_email_verified','users',['email_verified'])

    if 'email_verification_tokens' not in inspector.get_table_names():
        op.create_table(
            'email_verification_tokens',
            sa.Column('id',sa.String(length=36),primary_key=True),
            sa.Column('user_id',sa.String(length=36),sa.ForeignKey('users.id'),nullable=False),
            sa.Column('token_hash',sa.String(length=128),nullable=False,unique=True),
            sa.Column('expires_at',sa.DateTime(),nullable=False),
            sa.Column('used_at',sa.DateTime(),nullable=True),
            sa.Column('created_at',sa.DateTime(),nullable=False),
        )
        op.create_index('ix_email_verification_tokens_user_id','email_verification_tokens',['user_id'])
        op.create_index('ix_email_verification_tokens_token_hash','email_verification_tokens',['token_hash'],unique=True)
        op.create_index('ix_email_verification_tokens_expires_at','email_verification_tokens',['expires_at'])
        op.create_index('ix_email_verification_tokens_used_at','email_verification_tokens',['used_at'])
        op.create_index('ix_email_verification_tokens_created_at','email_verification_tokens',['created_at'])


def downgrade() -> None:
    op.drop_table('email_verification_tokens')
    op.drop_index('ix_users_email_verified',table_name='users')
    with op.batch_alter_table('users') as batch:
        batch.drop_column('email_verified_at')
        batch.drop_column('email_verified')
