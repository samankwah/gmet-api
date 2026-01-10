"""Add performance indexes for station and location lookups

Revision ID: a523ac4c68df
Revises: b738343e13a1
Create Date: 2026-01-07 21:43:02.848749+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a523ac4c68df'
down_revision: Union[str, None] = 'b738343e13a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create location_mappings table if it doesn't exist
    # This ensures compatibility with databases that don't have it from earlier migration branches
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'location_mappings' not in inspector.get_table_names():
        op.create_table(
            'location_mappings',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('location_name', sa.String(length=200), nullable=False, comment='Human-readable location name'),
            sa.Column('location_type', sa.String(length=50), nullable=False, comment='Type: city, region, district, alias'),
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

    # Index for case-insensitive station name search
    # Use LOWER() function for PostgreSQL, COLLATE NOCASE for SQLite
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('CREATE INDEX IF NOT EXISTS idx_station_name_lower ON stations (LOWER(name))')
        op.execute('CREATE INDEX IF NOT EXISTS idx_station_code_lower ON stations (LOWER(code))')
        op.execute('CREATE INDEX IF NOT EXISTS idx_location_active_name ON location_mappings (is_active, LOWER(location_name))')
    else:
        # SQLite
        op.execute('CREATE INDEX IF NOT EXISTS idx_station_name_lower ON stations (name COLLATE NOCASE)')
        op.execute('CREATE INDEX IF NOT EXISTS idx_station_code_lower ON stations (code COLLATE NOCASE)')
        op.execute('CREATE INDEX IF NOT EXISTS idx_location_active_name ON location_mappings (is_active, location_name COLLATE NOCASE)')


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS idx_station_name_lower')
    op.execute('DROP INDEX IF EXISTS idx_station_code_lower')
    op.execute('DROP INDEX IF EXISTS idx_location_active_name')

    # Check if we need to drop the location_mappings table
    # Only drop if it was created by this migration
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'location_mappings' in inspector.get_table_names():
        # Drop the indexes created with the table
        try:
            op.drop_index('idx_location_active', table_name='location_mappings')
            op.drop_index('idx_location_name_type', table_name='location_mappings')
            op.drop_index(op.f('ix_location_mappings_station_id'), table_name='location_mappings')
            op.drop_index(op.f('ix_location_mappings_location_type'), table_name='location_mappings')
            op.drop_index(op.f('ix_location_mappings_location_name'), table_name='location_mappings')
            op.drop_index(op.f('ix_location_mappings_id'), table_name='location_mappings')
        except:
            pass  # Indexes might not exist if created by another migration

        # Note: We don't drop the table itself in downgrade, as it might have been created
        # by migration 822df6608e6c. Only the specific indexes we added should be removed.
