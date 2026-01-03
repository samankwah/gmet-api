"""create initial schema with users stations and observations

Revision ID: acb5aa092b78
Revises: 
Create Date: 2026-01-03 21:39:39.772380+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acb5aa092b78'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('api_key', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_api_key'), 'users', ['api_key'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create stations table
    op.create_table(
        'stations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('region', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stations_code'), 'stations', ['code'], unique=True)
    op.create_index(op.f('ix_stations_id'), 'stations', ['id'], unique=False)
    op.create_index(op.f('ix_stations_name'), 'stations', ['name'], unique=False)
    op.create_index(op.f('ix_stations_region'), 'stations', ['region'], unique=False)
    op.create_index('idx_station_region_code', 'stations', ['region', 'code'], unique=False)

    # Create observations table
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
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_observations_id'), 'observations', ['id'], unique=False)
    op.create_index(op.f('ix_observations_station_id'), 'observations', ['station_id'], unique=False)
    op.create_index(op.f('ix_observations_timestamp'), 'observations', ['timestamp'], unique=False)
    op.create_index('idx_observation_station_timestamp', 'observations', ['station_id', 'timestamp'], unique=False)
    op.create_index('idx_observation_timestamp_station', 'observations', ['timestamp', 'station_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (to respect foreign key constraints)
    op.drop_index('idx_observation_timestamp_station', table_name='observations')
    op.drop_index('idx_observation_station_timestamp', table_name='observations')
    op.drop_index(op.f('ix_observations_timestamp'), table_name='observations')
    op.drop_index(op.f('ix_observations_station_id'), table_name='observations')
    op.drop_index(op.f('ix_observations_id'), table_name='observations')
    op.drop_table('observations')

    op.drop_index('idx_station_region_code', table_name='stations')
    op.drop_index(op.f('ix_stations_region'), table_name='stations')
    op.drop_index(op.f('ix_stations_name'), table_name='stations')
    op.drop_index(op.f('ix_stations_id'), table_name='stations')
    op.drop_index(op.f('ix_stations_code'), table_name='stations')
    op.drop_table('stations')

    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_api_key'), table_name='users')
    op.drop_table('users')
