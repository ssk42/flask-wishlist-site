"""Add price_extraction_log table

Revision ID: 4a8b3c9d1e2f
Revises: 3bf7272ee759
Create Date: 2026-01-25 01:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4a8b3c9d1e2f'
down_revision = '3bf7272ee759'
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists before creating
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'price_extraction_log' not in inspector.get_table_names():
        op.create_table('price_extraction_log',
                        sa.Column('id', sa.Integer(), nullable=False),
                        sa.Column('domain', sa.String(length=255), nullable=False),
                        sa.Column('url', sa.String(length=2048), nullable=True),
                        sa.Column('success', sa.Boolean(), nullable=False),
                        sa.Column('price', sa.Float(), nullable=True),
                        sa.Column('extraction_method', sa.String(length=50), nullable=True),
                        sa.Column('error_type', sa.String(length=50), nullable=True),
                        sa.Column('response_time_ms', sa.Integer(), nullable=True),
                        sa.Column('created_at', sa.DateTime(), nullable=True),
                        sa.PrimaryKeyConstraint('id')
                        )
        with op.batch_alter_table('price_extraction_log', schema=None) as batch_op:
            batch_op.create_index(
                batch_op.f('ix_price_extraction_log_created_at'),
                ['created_at'],
                unique=False)
            batch_op.create_index(
                batch_op.f('ix_price_extraction_log_domain'),
                ['domain'],
                unique=False)


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'price_extraction_log' in inspector.get_table_names():
        with op.batch_alter_table('price_extraction_log', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_price_extraction_log_domain'))
            batch_op.drop_index(
                batch_op.f('ix_price_extraction_log_created_at'))
        op.drop_table('price_extraction_log')
