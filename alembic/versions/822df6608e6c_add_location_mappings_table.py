"""add location mappings table

Revision ID: 822df6608e6c
Revises: acb5aa092b78
Create Date: 2026-01-03 21:56:59.803989+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '822df6608e6c'
down_revision: Union[str, None] = 'acb5aa092b78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create location_mappings table
    op.create_table(
        'location_mappings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('location_name', sa.String(), nullable=False, comment='Human-readable location name'),
        sa.Column('location_type', sa.String(), nullable=False, comment='Type: city, region, district, alias'),
        sa.Column('station_id', sa.Integer(), nullable=False, comment='Reference to weather station'),
        sa.Column('is_primary', sa.Boolean(), nullable=True, comment='Primary name for station'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='Whether mapping is active'),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_location_mappings_id'), 'location_mappings', ['id'], unique=False)
    op.create_index(op.f('ix_location_mappings_location_name'), 'location_mappings', ['location_name'], unique=False)
    op.create_index(op.f('ix_location_mappings_location_type'), 'location_mappings', ['location_type'], unique=False)
    op.create_index(op.f('ix_location_mappings_station_id'), 'location_mappings', ['station_id'], unique=False)
    op.create_index('idx_location_name_type', 'location_mappings', ['location_name', 'location_type'], unique=False)
    op.create_index('idx_location_active', 'location_mappings', ['is_active', 'location_name'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_location_active', table_name='location_mappings')
    op.drop_index('idx_location_name_type', table_name='location_mappings')
    op.drop_index(op.f('ix_location_mappings_station_id'), table_name='location_mappings')
    op.drop_index(op.f('ix_location_mappings_location_type'), table_name='location_mappings')
    op.drop_index(op.f('ix_location_mappings_location_name'), table_name='location_mappings')
    op.drop_index(op.f('ix_location_mappings_id'), table_name='location_mappings')

    # Drop table
    op.drop_table('location_mappings')
