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
    # Create the locations table
    op.create_table('locations',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_imei', sa.String(length=50), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('speed_kph', sa.SmallInteger(), nullable=True),
        sa.Column('heading', sa.SmallInteger(), nullable=True),
        sa.Column('engine_status', sa.Boolean(), nullable=True),
        sa.Column('fuel_level', sa.SmallInteger(), nullable=True),
        sa.Column('altitude_m', sa.Float(), nullable=True),
        sa.Column('satellite_count', sa.SmallInteger(), nullable=True),
        sa.PrimaryKeyConstraint('time', 'device_imei')
    )
    
    # Execute the TimescaleDB function to convert the table to a hypertable
    op.execute("SELECT create_hypertable('locations', 'time');")


def downgrade() -> None:
    op.drop_table('locations')
