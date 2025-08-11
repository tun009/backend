"""Create locations hypertable

Revision ID: 9b68a755da6d
Revises: 468c8900f6c8
Create Date: 2025-07-10 17:04:48.449024

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b68a755da6d'
down_revision: Union[str, None] = '468c8900f6c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Table 'locations' already created in migration 468c8900f6c8
    # This migration is now redundant - no action needed
    pass


def downgrade() -> None:
    # Table 'locations' managed by migration 468c8900f6c8
    # This migration is now redundant - no action needed
    pass
