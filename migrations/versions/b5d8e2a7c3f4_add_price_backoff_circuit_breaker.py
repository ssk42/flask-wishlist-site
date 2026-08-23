"""Add price_fail_streak and price_backoff_until to item

Price-fetch backoff circuit breaker (@spec AUTO-PRC-011..AUTO-PRC-016):
tracks consecutive automatic fetch failures per item and the time until
the sweep may retry it.

Revision ID: b5d8e2a7c3f4
Revises: e20431cbf8bc
Create Date: 2026-08-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5d8e2a7c3f4'
down_revision = 'e20431cbf8bc'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('item')}
    # server_default backs backfills the ~163 existing prod rows on Postgres;
    # kept permanently — harmless and keeps the column NOT NULL-safe.
    if 'price_fail_streak' not in columns:
        op.add_column('item',
            sa.Column('price_fail_streak', sa.Integer(), nullable=False,
                      server_default=sa.text('0')))
    if 'price_backoff_until' not in columns:
        op.add_column('item',
            sa.Column('price_backoff_until', sa.DateTime(), nullable=True))


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('item')}
    if 'price_backoff_until' in columns:
        op.drop_column('item', 'price_backoff_until')
    if 'price_fail_streak' in columns:
        op.drop_column('item', 'price_fail_streak')
