"""Add CHECK constraints for data validation

Revision ID: c574a722eb73
Revises: 446ac5c98233
Create Date: 2026-01-07 21:33:21.931270+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c574a722eb73'
down_revision: Union[str, None] = '446ac5c98233'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Relative humidity constraints (0-100%)
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_check_rh_range ON synoptic_observations
        ((CASE WHEN relative_humidity IS NOT NULL AND (relative_humidity < 0 OR relative_humidity > 100) THEN 1 END))
    ''')

    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_check_mean_rh_range ON daily_summaries
        ((CASE WHEN mean_rh IS NOT NULL AND (mean_rh < 0 OR mean_rh > 100) THEN 1 END))
    ''')

    # Wind direction constraint (0-360 degrees)
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_check_wind_dir_range ON synoptic_observations
        ((CASE WHEN wind_direction IS NOT NULL AND (wind_direction < 0 OR wind_direction > 360) THEN 1 END))
    ''')

    # Non-negative wind speed constraints
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_check_wind_speed_positive ON synoptic_observations
        ((CASE WHEN wind_speed IS NOT NULL AND wind_speed < 0 THEN 1 END))
    ''')

    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_check_daily_wind_speed_positive ON daily_summaries
        ((CASE WHEN wind_speed IS NOT NULL AND wind_speed < 0 THEN 1 END))
    ''')

    # Sunshine hours constraint (0-24 hours)
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_check_sunshine_range ON daily_summaries
        ((CASE WHEN sunshine_hours IS NOT NULL AND (sunshine_hours < 0 OR sunshine_hours > 24) THEN 1 END))
    ''')

    # Temperature relationship constraint (max >= min)
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_check_temp_range ON daily_summaries
        ((CASE WHEN temp_max IS NOT NULL AND temp_min IS NOT NULL AND temp_max < temp_min THEN 1 END))
    ''')


def downgrade() -> None:
    # Drop all constraint indexes
    op.execute('DROP INDEX IF EXISTS idx_check_rh_range')
    op.execute('DROP INDEX IF EXISTS idx_check_mean_rh_range')
    op.execute('DROP INDEX IF EXISTS idx_check_wind_dir_range')
    op.execute('DROP INDEX IF EXISTS idx_check_wind_speed_positive')
    op.execute('DROP INDEX IF EXISTS idx_check_daily_wind_speed_positive')
    op.execute('DROP INDEX IF EXISTS idx_check_sunshine_range')
    op.execute('DROP INDEX IF EXISTS idx_check_temp_range')
