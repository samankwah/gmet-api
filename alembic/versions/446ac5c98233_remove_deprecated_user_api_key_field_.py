"""Remove deprecated User.api_key field and add role

Revision ID: 446ac5c98233
Revises: bd8ec41a4d68
Create Date: 2026-01-07 21:32:09.678799+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '446ac5c98233'
down_revision: Union[str, None] = 'bd8ec41a4d68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add role column
    op.add_column('users', sa.Column('role', sa.String(), nullable=True))

    # Set default role for existing users
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")

    # Drop deprecated api_key column (stores plain text keys - security risk)
    # The new APIKey model uses bcrypt hashing
    op.drop_index('ix_users_api_key', table_name='users')
    op.drop_column('users', 'api_key')


def downgrade() -> None:
    # Add back api_key column
    op.add_column('users', sa.Column('api_key', sa.String(), nullable=True))
    op.create_index('ix_users_api_key', 'users', ['api_key'], unique=True)

    # Drop role column
    op.drop_column('users', 'role')
