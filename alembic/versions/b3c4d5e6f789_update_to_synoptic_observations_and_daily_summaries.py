"""Update to synoptic observations at 0600/0900/1200/1500 and daily summaries

Revision ID: b3c4d5e6f789
Revises: 822df6608e6c
Create Date: 2026-01-04 12:00:00.000000+00:00

This migration updates the data model to reflect GMet operational practices:
- Replaces generic 'observations' with 'synoptic_observations' for SYNOP schedule
- Adds 'daily_summaries' table for aggregated daily statistics
- Migrates existing data from observations to synoptic_observations
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f789'
down_revision: Union[str, None] = '822df6608e6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create synoptic_observations table
    op.create_table(
        'synoptic_observations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False, comment='Reference to the weather station'),
        sa.Column('obs_datetime', sa.DateTime(timezone=True), nullable=False, comment='Exact observation time'),
        sa.Column('temperature', sa.Float(), nullable=True, comment='Instantaneous air temperature in °C'),
        sa.Column('relative_humidity', sa.Integer(), nullable=True, comment='Relative humidity in % (0-100)'),
        sa.Column('wind_speed', sa.Float(), nullable=True, comment='Wind speed in m/s'),
        sa.Column('wind_direction', sa.Integer(), nullable=True, comment='Wind direction in degrees (0-360)'),
        sa.Column('pressure', sa.Float(), nullable=True, comment='Station pressure in hPa'),
        sa.Column('rainfall', sa.Float(), nullable=True, comment='Rainfall since last observation in mm'),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_id', 'obs_datetime', name='uq_synoptic_station_datetime')
    )
    
    # Create indexes for synoptic_observations
    op.create_index(op.f('ix_synoptic_observations_id'), 'synoptic_observations', ['id'], unique=False)
    op.create_index(op.f('ix_synoptic_observations_station_id'), 'synoptic_observations', ['station_id'], unique=False)
    op.create_index(op.f('ix_synoptic_observations_obs_datetime'), 'synoptic_observations', ['obs_datetime'], unique=False)
    op.create_index('idx_synoptic_station_datetime', 'synoptic_observations', ['station_id', 'obs_datetime'], unique=False)
    op.create_index('idx_synoptic_datetime_station', 'synoptic_observations', ['obs_datetime', 'station_id'], unique=False)
    op.create_index('idx_synoptic_datetime', 'synoptic_observations', ['obs_datetime'], unique=False)

    # Step 2: Migrate data from observations to synoptic_observations
    # Map: timestamp -> obs_datetime, humidity -> relative_humidity (cast to int), wind_direction -> int
    op.execute(text("""
        INSERT INTO synoptic_observations (
            id, created_at, updated_at, station_id, obs_datetime,
            temperature, relative_humidity, wind_speed, wind_direction,
            pressure, rainfall
        )
        SELECT 
            id, created_at, updated_at, station_id, timestamp as obs_datetime,
            temperature,
            CAST(humidity AS INTEGER) as relative_humidity,
            wind_speed,
            CAST(wind_direction AS INTEGER) as wind_direction,
            pressure,
            rainfall
        FROM observations
        WHERE EXISTS (SELECT 1 FROM stations WHERE stations.id = observations.station_id)
    """))

    # Step 3: Create daily_summaries table
    op.create_table(
        'daily_summaries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False, comment='Reference to the weather station'),
        sa.Column('date', sa.Date(), nullable=False, comment='Observation date'),
        sa.Column('temp_max', sa.Float(), nullable=True, comment='Maximum temperature in °C'),
        sa.Column('temp_max_time', sa.DateTime(timezone=True), nullable=True, comment='Time when maximum temperature was recorded'),
        sa.Column('temp_min', sa.Float(), nullable=True, comment='Minimum temperature in °C'),
        sa.Column('temp_min_time', sa.DateTime(timezone=True), nullable=True, comment='Time when minimum temperature was recorded'),
        sa.Column('rainfall_total', sa.Float(), nullable=True, comment='Total 24-hour rainfall in mm'),
        sa.Column('mean_rh', sa.Integer(), nullable=True, comment='Mean relative humidity in %'),
        sa.Column('max_wind_gust', sa.Float(), nullable=True, comment='Maximum wind gust in m/s'),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_id', 'date', name='uq_daily_station_date')
    )
    
    # Create indexes for daily_summaries
    op.create_index(op.f('ix_daily_summaries_id'), 'daily_summaries', ['id'], unique=False)
    op.create_index(op.f('ix_daily_summaries_station_id'), 'daily_summaries', ['station_id'], unique=False)
    op.create_index(op.f('ix_daily_summaries_date'), 'daily_summaries', ['date'], unique=False)
    op.create_index('idx_daily_station_date', 'daily_summaries', ['station_id', 'date'], unique=False)
    op.create_index('idx_daily_date', 'daily_summaries', ['date'], unique=False)

    # Step 4: Drop old observations table and its indexes
    # First drop indexes
    op.drop_index('idx_observation_timestamp_station', table_name='observations')
    op.drop_index('idx_observation_station_timestamp', table_name='observations')
    op.drop_index(op.f('ix_observations_timestamp'), table_name='observations')
    op.drop_index(op.f('ix_observations_station_id'), table_name='observations')
    op.drop_index(op.f('ix_observations_id'), table_name='observations')
    
    # Then drop the table
    op.drop_table('observations')


def downgrade() -> None:
    # Step 1: Recreate observations table (old structure)
    op.create_table(
        'observations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('humidity', sa.Float(), nullable=True),
        sa.Column('wind_speed', sa.Float(), nullable=True),
        sa.Column('wind_direction', sa.Float(), nullable=True),
        sa.Column('rainfall', sa.Float(), nullable=True),
        sa.Column('pressure', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate indexes for observations
    op.create_index(op.f('ix_observations_id'), 'observations', ['id'], unique=False)
    op.create_index(op.f('ix_observations_station_id'), 'observations', ['station_id'], unique=False)
    op.create_index(op.f('ix_observations_timestamp'), 'observations', ['timestamp'], unique=False)
    op.create_index('idx_observation_station_timestamp', 'observations', ['station_id', 'timestamp'], unique=False)
    op.create_index('idx_observation_timestamp_station', 'observations', ['timestamp', 'station_id'], unique=False)

    # Step 2: Migrate data back from synoptic_observations to observations
    op.execute(text("""
        INSERT INTO observations (
            id, created_at, updated_at, station_id, timestamp,
            temperature, humidity, wind_speed, wind_direction,
            pressure, rainfall
        )
        SELECT 
            id, created_at, updated_at, station_id, obs_datetime as timestamp,
            temperature,
            CAST(relative_humidity AS FLOAT) as humidity,
            wind_speed,
            CAST(wind_direction AS FLOAT) as wind_direction,
            pressure,
            rainfall
        FROM synoptic_observations
        WHERE EXISTS (SELECT 1 FROM stations WHERE stations.id = synoptic_observations.station_id)
    """))

    # Step 3: Drop daily_summaries table and indexes
    op.drop_index('idx_daily_date', table_name='daily_summaries')
    op.drop_index('idx_daily_station_date', table_name='daily_summaries')
    op.drop_index(op.f('ix_daily_summaries_date'), table_name='daily_summaries')
    op.drop_index(op.f('ix_daily_summaries_station_id'), table_name='daily_summaries')
    op.drop_index(op.f('ix_daily_summaries_id'), table_name='daily_summaries')
    op.drop_table('daily_summaries')

    # Step 4: Drop synoptic_observations table and indexes
    op.drop_index('idx_synoptic_datetime', table_name='synoptic_observations')
    op.drop_index('idx_synoptic_datetime_station', table_name='synoptic_observations')
    op.drop_index('idx_synoptic_station_datetime', table_name='synoptic_observations')
    op.drop_index(op.f('ix_synoptic_observations_obs_datetime'), table_name='synoptic_observations')
    op.drop_index(op.f('ix_synoptic_observations_station_id'), table_name='synoptic_observations')
    op.drop_index(op.f('ix_synoptic_observations_id'), table_name='synoptic_observations')
    op.drop_table('synoptic_observations')

