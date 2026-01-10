"""Add individual RH readings at SYNOP times

Revision ID: fec96312ec88
Revises: a523ac4c68df
Create Date: 2026-01-08 21:07:23.827155+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fec96312ec88'
down_revision: Union[str, None] = 'a523ac4c68df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add individual RH reading columns for each SYNOP observation time
    op.add_column('daily_summaries', sa.Column('rh_0600', sa.Integer(), nullable=True,
                  comment='Relative humidity at 0600 UTC in % (0-100)'))
    op.add_column('daily_summaries', sa.Column('rh_0900', sa.Integer(), nullable=True,
                  comment='Relative humidity at 0900 UTC in % (0-100)'))
    op.add_column('daily_summaries', sa.Column('rh_1200', sa.Integer(), nullable=True,
                  comment='Relative humidity at 1200 UTC in % (0-100)'))
    op.add_column('daily_summaries', sa.Column('rh_1500', sa.Integer(), nullable=True,
                  comment='Relative humidity at 1500 UTC in % (0-100)'))


def downgrade() -> None:
    # Remove individual RH columns
    op.drop_column('daily_summaries', 'rh_1500')
    op.drop_column('daily_summaries', 'rh_1200')
    op.drop_column('daily_summaries', 'rh_0900')
    op.drop_column('daily_summaries', 'rh_0600')
