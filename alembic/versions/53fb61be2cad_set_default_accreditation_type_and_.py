"""set default accreditation type and backfill

Revision ID: 53fb61be2cad
Revises: 42bd41ea783a
Create Date: 2026-03-20 20:30:19.749664

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53fb61be2cad'
down_revision: Union[str, None] = '42bd41ea783a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update existing nulls to Re-Accreditation
    op.execute("UPDATE schools SET accreditation_type = 'Re-Accreditation' WHERE accreditation_type IS NULL")
    op.execute("UPDATE bece_schools SET accreditation_type = 'Re-Accreditation' WHERE accreditation_type IS NULL")
    
    # 2. Set server default for future records
    op.alter_column('schools', 'accreditation_type', server_default='Re-Accreditation')
    op.alter_column('bece_schools', 'accreditation_type', server_default='Re-Accreditation')


def downgrade() -> None:
    op.alter_column('schools', 'accreditation_type', server_default=None)
    op.alter_column('bece_schools', 'accreditation_type', server_default=None)
