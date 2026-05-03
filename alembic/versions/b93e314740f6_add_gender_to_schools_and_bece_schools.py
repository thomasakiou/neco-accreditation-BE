"""add gender to schools and bece_schools

Revision ID: b93e314740f6
Revises: c27c66715bdb
Create Date: 2026-05-03 08:19:16.371210

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b93e314740f6'
down_revision: Union[str, None] = 'c27c66715bdb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('schools', sa.Column('gender', sa.String(), nullable=True))
    op.add_column('bece_schools', sa.Column('gender', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('bece_schools', 'gender')
    op.drop_column('schools', 'gender')
