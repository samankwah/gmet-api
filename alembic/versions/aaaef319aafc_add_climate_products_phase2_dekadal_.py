"""add_climate_products_phase2_dekadal_seasonal_annual_normals

Revision ID: aaaef319aafc
Revises: a7dfdca06c4f
Create Date: 2026-01-10 04:34:35.066484+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aaaef319aafc'
down_revision: Union[str, None] = 'a7dfdca06c4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create dekadal_summaries table
    op.create_table(
        'dekadal_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False, comment='Reference to the weather station'),
        sa.Column('year', sa.Integer(), nullable=False, comment='Calendar year'),
        sa.Column('month', sa.Integer(), nullable=False, comment='Month number (1-12)'),
        sa.Column('dekad', sa.Integer(), nullable=False, comment='Dekad number: 1 (days 1-10), 2 (days 11-20), 3 (days 21-EOM)'),
        sa.Column('start_date', sa.Date(), nullable=False, comment='Start date of the dekad'),
        sa.Column('end_date', sa.Date(), nullable=False, comment='End date of the dekad'),
        sa.Column('rainfall_total', sa.Float(), nullable=True, comment='Total dekadal rainfall in mm (SUM of daily values)'),
        sa.Column('rainfall_anomaly', sa.Float(), nullable=True, comment='Rainfall anomaly vs 30-year normal in mm (absolute difference)'),
        sa.Column('rainfall_anomaly_percent', sa.Float(), nullable=True, comment='Rainfall anomaly as percentage of normal'),
        sa.Column('rainy_days', sa.Integer(), nullable=True, comment='Number of days with rainfall >= 1mm'),
        sa.Column('temp_max_mean', sa.Float(), nullable=True, comment='Mean of daily maximum temperatures in °C'),
        sa.Column('temp_min_mean', sa.Float(), nullable=True, comment='Mean of daily minimum temperatures in °C'),
        sa.Column('temp_max_absolute', sa.Float(), nullable=True, comment='Absolute maximum temperature in °C during the dekad'),
        sa.Column('temp_min_absolute', sa.Float(), nullable=True, comment='Absolute minimum temperature in °C during the dekad'),
        sa.Column('mean_rh', sa.Integer(), nullable=True, comment='Mean relative humidity in % (average of daily means)'),
        sa.Column('sunshine_total', sa.Float(), nullable=True, comment='Total sunshine hours (SUM of daily values)'),
        sa.CheckConstraint('dekad >= 1 AND dekad <= 3', name='check_dekad_valid'),
        sa.CheckConstraint('month >= 1 AND month <= 12', name='check_dekadal_month_valid'),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_id', 'year', 'month', 'dekad', name='uq_dekadal_station_year_month_dekad')
    )
    op.create_index('idx_dekadal_station_year_month', 'dekadal_summaries', ['station_id', 'year', 'month'])

    # Create seasonal_summaries table
    op.create_table(
        'seasonal_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False, comment='Reference to the weather station'),
        sa.Column('year', sa.Integer(), nullable=False, comment='Calendar year (for DJF, year refers to December-January year)'),
        sa.Column('season', sa.String(3), nullable=False, comment='Season code: MAM, JJA, SON, or DJF'),
        sa.Column('start_date', sa.Date(), nullable=False, comment='Start date of the season'),
        sa.Column('end_date', sa.Date(), nullable=False, comment='End date of the season'),
        sa.Column('rainfall_total', sa.Float(), nullable=True, comment='Total seasonal rainfall in mm (SUM of daily values)'),
        sa.Column('rainfall_anomaly', sa.Float(), nullable=True, comment='Rainfall anomaly vs 30-year normal in mm (absolute difference)'),
        sa.Column('rainfall_anomaly_percent', sa.Float(), nullable=True, comment='Rainfall anomaly as percentage of normal'),
        sa.Column('rainy_days', sa.Integer(), nullable=True, comment='Number of days with rainfall >= 1mm'),
        sa.Column('onset_date', sa.Date(), nullable=True, comment='Date when rainy season begins (WMO criteria)'),
        sa.Column('cessation_date', sa.Date(), nullable=True, comment='Date when rainy season ends'),
        sa.Column('season_length_days', sa.Integer(), nullable=True, comment='Number of days between onset and cessation (growing season length)'),
        sa.Column('max_dry_spell_days', sa.Integer(), nullable=True, comment='Maximum consecutive days without rain (>= 1mm)'),
        sa.Column('dry_spells_count', sa.Integer(), nullable=True, comment='Number of dry spells >= 7 consecutive days'),
        sa.Column('temp_max_mean', sa.Float(), nullable=True, comment='Mean of daily maximum temperatures in °C'),
        sa.Column('temp_min_mean', sa.Float(), nullable=True, comment='Mean of daily minimum temperatures in °C'),
        sa.Column('temp_anomaly', sa.Float(), nullable=True, comment='Temperature anomaly vs 30-year normal in °C'),
        sa.Column('hot_days_count', sa.Integer(), nullable=True, comment='Number of days with Tmax > 35°C'),
        sa.Column('mean_rh', sa.Integer(), nullable=True, comment='Mean relative humidity in %'),
        sa.Column('sunshine_total', sa.Float(), nullable=True, comment='Total sunshine hours (SUM of daily values)'),
        sa.CheckConstraint("season IN ('MAM', 'JJA', 'SON', 'DJF')", name='check_season_valid'),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_id', 'year', 'season', name='uq_seasonal_station_year_season')
    )
    op.create_index('idx_seasonal_station_year', 'seasonal_summaries', ['station_id', 'year'])

    # Create annual_summaries table
    op.create_table(
        'annual_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False, comment='Reference to the weather station'),
        sa.Column('year', sa.Integer(), nullable=False, comment='Calendar year'),
        sa.Column('rainfall_total', sa.Float(), nullable=True, comment='Total annual rainfall in mm (SUM of 365 daily values)'),
        sa.Column('rainfall_anomaly', sa.Float(), nullable=True, comment='Rainfall anomaly vs 30-year normal in mm'),
        sa.Column('rainfall_anomaly_percent', sa.Float(), nullable=True, comment='Rainfall anomaly as percentage of normal'),
        sa.Column('rainfall_days', sa.Integer(), nullable=True, comment='Number of days with rainfall >= 1mm'),
        sa.Column('max_daily_rainfall', sa.Float(), nullable=True, comment='Maximum daily rainfall in mm during the year'),
        sa.Column('max_daily_rainfall_date', sa.Date(), nullable=True, comment='Date of maximum daily rainfall'),
        sa.Column('temp_max_absolute', sa.Float(), nullable=True, comment='Absolute maximum temperature in °C during the year'),
        sa.Column('temp_max_absolute_date', sa.Date(), nullable=True, comment='Date of absolute maximum temperature'),
        sa.Column('temp_min_absolute', sa.Float(), nullable=True, comment='Absolute minimum temperature in °C during the year'),
        sa.Column('temp_min_absolute_date', sa.Date(), nullable=True, comment='Date of absolute minimum temperature'),
        sa.Column('temp_mean_annual', sa.Float(), nullable=True, comment='Mean annual temperature in °C'),
        sa.Column('temp_anomaly', sa.Float(), nullable=True, comment='Temperature anomaly vs 30-year normal in °C'),
        sa.Column('hot_days_count', sa.Integer(), nullable=True, comment='Number of days with Tmax > 35°C'),
        sa.Column('very_hot_days_count', sa.Integer(), nullable=True, comment='Number of days with Tmax > 40°C'),
        sa.Column('heavy_rain_days', sa.Integer(), nullable=True, comment='Number of days with rainfall > 50mm'),
        sa.Column('mean_rh_annual', sa.Integer(), nullable=True, comment='Mean annual relative humidity in %'),
        sa.Column('sunshine_total', sa.Float(), nullable=True, comment='Total annual sunshine hours (SUM of 365 daily values)'),
        sa.Column('data_completeness_percent', sa.Float(), nullable=True, comment='Percentage of days with valid observations'),
        sa.CheckConstraint('data_completeness_percent >= 0 AND data_completeness_percent <= 100', name='check_annual_completeness_valid'),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_id', 'year', name='uq_annual_station_year')
    )
    op.create_index('idx_annual_station_year', 'annual_summaries', ['station_id', 'year'])
    op.create_index('idx_annual_year', 'annual_summaries', ['year'])

    # Create climate_normals table
    op.create_table(
        'climate_normals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False, comment='Reference to the weather station'),
        sa.Column('normal_period_start', sa.Integer(), nullable=False, comment='Start year of the 30-year normal period (e.g., 1991)'),
        sa.Column('normal_period_end', sa.Integer(), nullable=False, comment='End year of the 30-year normal period (e.g., 2020)'),
        sa.Column('timescale', sa.String(20), nullable=False, comment="Timescale: 'monthly', 'dekadal', 'seasonal', or 'annual'"),
        sa.Column('month', sa.Integer(), nullable=True, comment='Month number (1-12) for monthly and dekadal normals'),
        sa.Column('dekad', sa.Integer(), nullable=True, comment='Dekad number (1-3) for dekadal normals only'),
        sa.Column('season', sa.String(3), nullable=True, comment='Season code (MAM, JJA, SON, DJF) for seasonal normals only'),
        sa.Column('rainfall_normal', sa.Float(), nullable=True, comment='30-year mean rainfall in mm for this period'),
        sa.Column('rainfall_std', sa.Float(), nullable=True, comment='Standard deviation of rainfall across 30 years'),
        sa.Column('temp_max_normal', sa.Float(), nullable=True, comment='30-year mean of maximum temperatures in °C'),
        sa.Column('temp_min_normal', sa.Float(), nullable=True, comment='30-year mean of minimum temperatures in °C'),
        sa.Column('temp_mean_normal', sa.Float(), nullable=True, comment='30-year mean temperature in °C'),
        sa.Column('temp_std', sa.Float(), nullable=True, comment='Standard deviation of mean temperature across 30 years'),
        sa.Column('sunshine_normal', sa.Float(), nullable=True, comment='30-year mean sunshine hours for this period'),
        sa.Column('years_with_data', sa.Integer(), nullable=True, comment='Number of years (out of 30) with sufficient data'),
        sa.Column('data_completeness_percent', sa.Float(), nullable=True, comment='Percentage of expected data available across the 30-year period'),
        sa.CheckConstraint("timescale IN ('monthly', 'dekadal', 'seasonal', 'annual')", name='check_timescale_valid'),
        sa.CheckConstraint('month IS NULL OR (month >= 1 AND month <= 12)', name='check_climate_normal_month_valid'),
        sa.CheckConstraint('dekad IS NULL OR (dekad >= 1 AND dekad <= 3)', name='check_climate_normal_dekad_valid'),
        sa.CheckConstraint("season IS NULL OR season IN ('MAM', 'JJA', 'SON', 'DJF')", name='check_climate_normal_season_valid'),
        sa.CheckConstraint('data_completeness_percent >= 0 AND data_completeness_percent <= 100', name='check_climate_normal_completeness_valid'),
        sa.CheckConstraint('years_with_data >= 0 AND years_with_data <= 30', name='check_years_with_data_valid'),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_id', 'normal_period_start', 'normal_period_end', 'timescale', 'month', 'dekad', 'season', name='uq_climate_normal_unique')
    )
    op.create_index('idx_climate_normal_station_period', 'climate_normals', ['station_id', 'normal_period_start', 'normal_period_end'])
    op.create_index('idx_climate_normal_timescale', 'climate_normals', ['timescale'])


def downgrade() -> None:
    # Drop Phase 2 tables in reverse order
    op.drop_index('idx_climate_normal_timescale', table_name='climate_normals')
    op.drop_index('idx_climate_normal_station_period', table_name='climate_normals')
    op.drop_table('climate_normals')

    op.drop_index('idx_annual_year', table_name='annual_summaries')
    op.drop_index('idx_annual_station_year', table_name='annual_summaries')
    op.drop_table('annual_summaries')

    op.drop_index('idx_seasonal_station_year', table_name='seasonal_summaries')
    op.drop_table('seasonal_summaries')

    op.drop_index('idx_dekadal_station_year_month', table_name='dekadal_summaries')
    op.drop_table('dekadal_summaries')
