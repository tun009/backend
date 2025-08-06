"""create_device_logs_table

Revision ID: 9547035acf0b
Revises: e38c9097fa22
Create Date: 2025-08-06 13:41:11.081268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9547035acf0b'
down_revision: Union[str, Sequence[str], None] = 'e38c9097fa22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Tạo bảng device_logs
    op.create_table('device_logs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('journey_session_id', sa.BigInteger(), nullable=False),
        sa.Column('device_imei', sa.String(length=50), nullable=False),
        sa.Column('mqtt_response', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['journey_session_id'], ['journey_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tạo indexes cho performance
    op.create_index('idx_logs_journey_time', 'device_logs', 
                   ['journey_session_id', 'collected_at'], 
                   postgresql_ops={'collected_at': 'DESC'})
    
    op.create_index('idx_logs_device_time', 'device_logs', 
                   ['device_imei', 'collected_at'], 
                   postgresql_ops={'collected_at': 'DESC'})
    
    # Index đơn giản cho recent data (không dùng NOW() trong WHERE)
    op.create_index('idx_logs_recent', 'device_logs', 
                   ['collected_at'], 
                   postgresql_ops={'collected_at': 'DESC'})


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_logs_recent', table_name='device_logs')
    op.drop_index('idx_logs_device_time', table_name='device_logs')
    op.drop_index('idx_logs_journey_time', table_name='device_logs')
    op.drop_table('device_logs')
