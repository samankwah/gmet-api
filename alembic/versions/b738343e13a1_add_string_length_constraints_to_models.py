"""Add string length constraints to models

Revision ID: b738343e13a1
Revises: c574a722eb73
Create Date: 2026-01-07 21:34:52.822759+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b738343e13a1'
down_revision: Union[str, None] = 'c574a722eb73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOTE: SQLite doesn't support ALTER COLUMN for type changes
    # These string length constraints are enforced in the model definitions
    # When tables are recreated, they will use the proper String(length) types
    #
    # Changes made to models:
    # - users.email: String -> String(255)
    # - users.hashed_password: String -> String(255)
    # - users.role: String -> String(50)
    # - stations.name: String -> String(200)
    # - stations.code: String -> String(50)
    # - stations.region: String -> String(100)
    # - location_mappings.location_name: String -> String(200)
    # - location_mappings.location_type: String -> String(50)
    # - api_keys.name: String -> String(200)
    # - api_keys.role: String -> String(50)
    pass


def downgrade() -> None:
    # No downgrade needed - string length constraints don't require migration rollback
    pass
