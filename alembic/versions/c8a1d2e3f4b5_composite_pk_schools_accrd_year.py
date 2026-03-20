"""composite PK (code, accrd_year) for schools and bece_schools

Revision ID: c8a1d2e3f4b5
Revises: 1e67131b08f7
Create Date: 2026-03-07 07:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8a1d2e3f4b5'
down_revision: Union[str, None] = '1e67131b08f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fill any NULL accrd_year values with '2025' before making non-nullable
    op.execute("UPDATE schools SET accrd_year = '2025' WHERE accrd_year IS NULL")
    op.execute("UPDATE bece_schools SET accrd_year = '2025' WHERE accrd_year IS NULL")

    # Drop existing primary key on 'code' alone
    op.drop_constraint('schools_pkey', 'schools', type_='primary')
    op.drop_constraint('bece_schools_pkey', 'bece_schools', type_='primary')

    # Make accrd_year non-nullable with a server default
    op.alter_column('schools', 'accrd_year', nullable=False, server_default='2025')
    op.alter_column('bece_schools', 'accrd_year', nullable=False, server_default='2025')

    # Create composite primary key
    op.create_primary_key('schools_pkey', 'schools', ['code', 'accrd_year'])
    op.create_primary_key('bece_schools_pkey', 'bece_schools', ['code', 'accrd_year'])


def downgrade() -> None:
    # Drop composite primary key
    op.drop_constraint('schools_pkey', 'schools', type_='primary')
    op.drop_constraint('bece_schools_pkey', 'bece_schools', type_='primary')

    # Remove non-nullable and server default
    op.alter_column('schools', 'accrd_year', nullable=True, server_default=None)
    op.alter_column('bece_schools', 'accrd_year', nullable=True, server_default=None)

    # Restore original primary key on code alone
    # NOTE: This may fail if duplicate codes exist across years
    op.create_primary_key('schools_pkey', 'schools', ['code'])
    op.create_primary_key('bece_schools_pkey', 'bece_schools', ['code'])
