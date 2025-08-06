"""update_journey_sessions_remove_server_default

Revision ID: 7ebd02b5f8f1
Revises: aa34f68b0906
Create Date: 2025-08-06 15:56:25.077345

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ebd02b5f8f1'
down_revision: Union[str, Sequence[str], None] = 'aa34f68b0906'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove server default from start_time and make end_time NOT NULL."""
    # Remove server default from start_time
    op.alter_column('journey_sessions', 'start_time',
                   existing_type=sa.DateTime(timezone=True),
                   nullable=False,
                   server_default=None)

    # Make end_time NOT NULL (but first set default for existing NULL values)
    op.execute("UPDATE journey_sessions SET end_time = start_time + INTERVAL '8 hours' WHERE end_time IS NULL")
    op.alter_column('journey_sessions', 'end_time',
                   existing_type=sa.DateTime(timezone=True),
                   nullable=False)


def downgrade() -> None:
    """Restore server default to start_time and make end_time nullable."""
    # Make end_time nullable again
    op.alter_column('journey_sessions', 'end_time',
                   existing_type=sa.DateTime(timezone=True),
                   nullable=True)

    # Restore server default to start_time
    op.alter_column('journey_sessions', 'start_time',
                   existing_type=sa.DateTime(timezone=True),
                   nullable=False,
                   server_default=sa.text('now()'))
