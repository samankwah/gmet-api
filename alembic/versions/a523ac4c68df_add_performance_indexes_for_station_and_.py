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
    # Index for case-insensitive station name search
    # SQLite: CREATE INDEX uses COLLATE NOCASE for case-insensitive
    op.execute('CREATE INDEX IF NOT EXISTS idx_station_name_lower ON stations (name COLLATE NOCASE)')

    # Index for case-insensitive station code search
    op.execute('CREATE INDEX IF NOT EXISTS idx_station_code_lower ON stations (code COLLATE NOCASE)')

    # Composite index for active location lookups
    op.execute('CREATE INDEX IF NOT EXISTS idx_location_active_name ON location_mappings (is_active, location_name COLLATE NOCASE)')


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS idx_station_name_lower')
    op.execute('DROP INDEX IF EXISTS idx_station_code_lower')
    op.execute('DROP INDEX IF EXISTS idx_location_active_name')
