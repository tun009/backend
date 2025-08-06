"""add_status_to_journey_sessions

Revision ID: aa34f68b0906
Revises: 9547035acf0b
Create Date: 2025-08-06 13:42:48.361251

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa34f68b0906'
down_revision: Union[str, Sequence[str], None] = '9547035acf0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Thêm cột status
    op.add_column('journey_sessions', 
                 sa.Column('status', sa.String(length=20), 
                          server_default='pending', nullable=True))
    
    # Thêm cột activated_at
    op.add_column('journey_sessions', 
                 sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True))
    
    # Tạo index cho status
    op.create_index('idx_journey_status_time', 'journey_sessions', 
                   ['status', 'start_time', 'end_time'])
    
    # Update existing records to have proper status
    op.execute("""
        UPDATE journey_sessions 
        SET status = CASE 
            WHEN end_time IS NULL OR end_time > NOW() THEN 'active'
            ELSE 'completed'
        END
        WHERE status IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_journey_status_time', table_name='journey_sessions')
    op.drop_column('journey_sessions', 'activated_at')
    op.drop_column('journey_sessions', 'status')
