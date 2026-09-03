"""Add item archived_at for wishlist archive

Wishlist archive (@spec OWN-ITEM-009..OWN-ITEM-017):
nullable timestamp marking an archived item; None = active.

Revision ID: c7d9e1f2a3b4
Revises: b5d8e2a7c3f4
Create Date: 2026-09-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7d9e1f2a3b4'
down_revision = 'b5d8e2a7c3f4'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('item')}
    if 'archived_at' not in columns:
        op.add_column('item',
            sa.Column('archived_at', sa.DateTime(), nullable=True))
    indexes = {i['name'] for i in inspector.get_indexes('item')}
    if 'ix_item_archived_at' not in indexes:
        op.create_index('ix_item_archived_at', 'item', ['archived_at'],
                        unique=False)


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = {i['name'] for i in inspector.get_indexes('item')}
    if 'ix_item_archived_at' in indexes:
        op.drop_index('ix_item_archived_at', table_name='item')
    columns = {c['name'] for c in inspector.get_columns('item')}
    if 'archived_at' in columns:
        op.drop_column('item', 'archived_at')
