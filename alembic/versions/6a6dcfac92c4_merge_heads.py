"""merge heads

Revision ID: 6a6dcfac92c4
Revises: a632f91e0eb9, eb1a529244cb
Create Date: 2026-01-04 11:46:18.056099+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a6dcfac92c4'
down_revision: Union[str, None] = ('a632f91e0eb9', 'eb1a529244cb')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
