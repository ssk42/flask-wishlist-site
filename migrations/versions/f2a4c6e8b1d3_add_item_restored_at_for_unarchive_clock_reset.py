"""Add item restored_at for unarchive clock reset

Unarchive clock reset (@spec OWN-ITEM-021, issue #106):
nullable timestamp recording the most recent unarchive; the
automatic archive sweep measures an item's age from the later
of created_at and restored_at, so a restore earns a fresh
10 months before the sweep can archive the item again.

Revision ID: f2a4c6e8b1d3
Revises: c7d9e1f2a3b4
Create Date: 2026-11-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a4c6e8b1d3'
down_revision = 'c7d9e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('item')}
    if 'restored_at' not in columns:
        op.add_column('item',
            sa.Column('restored_at', sa.DateTime(), nullable=True))


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('item')}
    if 'restored_at' in columns:
        op.drop_column('item', 'restored_at')
