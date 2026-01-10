"""add_climate_products_phase1_weekly_monthly

Revision ID: a7dfdca06c4f
Revises: fec96312ec88
Create Date: 2026-01-09 20:07:31.690260+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7dfdca06c4f'
down_revision: Union[str, None] = 'fec96312ec88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create weekly_summaries and monthly_summaries tables for Phase 1 climate products."""

    # Create weekly_summaries table
    op.create_table(
        'weekly_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False, comment='Reference to the weather station'),
        sa.Column('year', sa.Integer(), nullable=False, comment='ISO 8601 year (may differ from calendar year for week 1)'),
        sa.Column('week_number', sa.Integer(), nullable=False, comment='ISO 8601 week number (1-53)'),
        sa.Column('start_date', sa.Date(), nullable=False, comment='Monday start date of the week'),
        sa.Column('end_date', sa.Date(), nullable=False, comment='Sunday end date of the week'),
        sa.Column('rainfall_total', sa.Float(), nullable=True, comment='Total weekly rainfall in mm (SUM of 7 daily values)'),
        sa.Column('wet_days_count', sa.Integer(), nullable=True, comment='Number of days with rainfall >= 1mm'),
        sa.Column('max_daily_rainfall', sa.Float(), nullable=True, comment='Maximum daily rainfall in mm during the week'),
        sa.Column('temp_max_mean', sa.Float(), nullable=True, comment='Mean of daily maximum temperatures in °C'),
        sa.Column('temp_min_mean', sa.Float(), nullable=True, comment='Mean of daily minimum temperatures in °C'),
        sa.Column('temp_max_absolute', sa.Float(), nullable=True, comment='Absolute maximum temperature in °C during the week'),
        sa.Column('temp_min_absolute', sa.Float(), nullable=True, comment='Absolute minimum temperature in °C during the week'),
        sa.Column('mean_rh', sa.Integer(), nullable=True, comment='Mean relative humidity in % (average of daily means)'),
        sa.Column('mean_wind_speed', sa.Float(), nullable=True, comment='Mean wind speed in m/s (average of daily means)'),
        sa.Column('sunshine_total', sa.Float(), nullable=True, comment='Total sunshine hours (SUM of 7 daily values, max ~84 hours)'),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_id', 'year', 'week_number', name='uq_weekly_station_year_week')
    )

    # Create indexes for weekly_summaries
    op.create_index('idx_weekly_station_year_week', 'weekly_summaries', ['station_id', 'year', 'week_number'])
    op.create_index('idx_weekly_year', 'weekly_summaries', ['year'])
    op.create_index('idx_weekly_station_id', 'weekly_summaries', ['station_id'])

    # Create monthly_summaries table
    op.create_table(
        'monthly_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False, comment='Reference to the weather station'),
        sa.Column('year', sa.Integer(), nullable=False, comment='Calendar year'),
        sa.Column('month', sa.Integer(), nullable=False, comment='Month number (1-12)'),
        sa.Column('rainfall_total', sa.Float(), nullable=True, comment='Total monthly rainfall in mm (SUM of daily values)'),
        sa.Column('rainfall_anomaly', sa.Float(), nullable=True, comment='Rainfall anomaly vs 30-year normal in mm (absolute difference)'),
        sa.Column('rainfall_anomaly_percent', sa.Float(), nullable=True, comment='Rainfall anomaly as percentage of normal'),
        sa.Column('rainfall_days', sa.Integer(), nullable=True, comment='Number of days with rainfall >= 1mm'),
        sa.Column('max_daily_rainfall', sa.Float(), nullable=True, comment='Maximum daily rainfall in mm during the month'),
        sa.Column('temp_max_mean', sa.Float(), nullable=True, comment='Mean of daily maximum temperatures in °C'),
        sa.Column('temp_min_mean', sa.Float(), nullable=True, comment='Mean of daily minimum temperatures in °C'),
        sa.Column('temp_mean', sa.Float(), nullable=True, comment='Mean temperature in °C (average of temp_max_mean and temp_min_mean)'),
        sa.Column('temp_max_absolute', sa.Float(), nullable=True, comment='Absolute maximum temperature in °C during the month'),
        sa.Column('temp_min_absolute', sa.Float(), nullable=True, comment='Absolute minimum temperature in °C during the month'),
        sa.Column('temp_anomaly', sa.Float(), nullable=True, comment='Temperature anomaly vs 30-year normal in °C (absolute difference)'),
        sa.Column('mean_rh', sa.Integer(), nullable=True, comment='Mean relative humidity in % (average of daily means)'),
        sa.Column('mean_wind_speed', sa.Float(), nullable=True, comment='Mean wind speed in m/s (average of daily means)'),
        sa.Column('sunshine_total', sa.Float(), nullable=True, comment='Total sunshine hours (SUM of daily values)'),
        sa.Column('days_with_data', sa.Integer(), nullable=True, comment='Number of days with valid observations in the month'),
        sa.Column('data_completeness_percent', sa.Float(), nullable=True, comment='Percentage of days with valid observations (days_with_data / days_in_month * 100)'),
        sa.CheckConstraint('month >= 1 AND month <= 12', name='check_month_valid'),
        sa.CheckConstraint('data_completeness_percent >= 0 AND data_completeness_percent <= 100', name='check_completeness_valid'),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_id', 'year', 'month', name='uq_monthly_station_year_month')
    )

    # Create indexes for monthly_summaries
    op.create_index('idx_monthly_station_year_month', 'monthly_summaries', ['station_id', 'year', 'month'])
    op.create_index('idx_monthly_year_month', 'monthly_summaries', ['year', 'month'])
    op.create_index('idx_monthly_station_id', 'monthly_summaries', ['station_id'])


def downgrade() -> None:
    """Drop weekly_summaries and monthly_summaries tables."""

    # Drop indexes first
    op.drop_index('idx_monthly_station_id', table_name='monthly_summaries')
    op.drop_index('idx_monthly_year_month', table_name='monthly_summaries')
    op.drop_index('idx_monthly_station_year_month', table_name='monthly_summaries')

    op.drop_index('idx_weekly_station_id', table_name='weekly_summaries')
    op.drop_index('idx_weekly_year', table_name='weekly_summaries')
    op.drop_index('idx_weekly_station_year_week', table_name='weekly_summaries')

    # Drop tables
    op.drop_table('monthly_summaries')
    op.drop_table('weekly_summaries')
