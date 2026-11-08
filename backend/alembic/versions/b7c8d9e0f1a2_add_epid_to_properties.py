"""add epid to properties

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-10-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1a2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('properties', sa.Column('epid', sa.String(10), nullable=True))
    op.create_index('ix_properties_epid', 'properties', ['epid'])


def downgrade():
    op.drop_index('ix_properties_epid', table_name='properties')
    op.drop_column('properties', 'epid')
