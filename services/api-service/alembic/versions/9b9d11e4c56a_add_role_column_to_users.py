"""add_role_column_to_users

Revision ID: 9b9d11e4c56a
Revises: 9b68a755da6d
Create Date: 2025-07-17 09:34:55.878677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b9d11e4c56a'
down_revision: Union[str, Sequence[str], None] = '9b68a755da6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add role column to users table
    op.add_column('users', sa.Column('role', sa.String(50), nullable=True))
    
    # Migrate existing data: copy role name from roles table to users.role
    # For users with role_id, set role = roles.name
    # For users without role_id, set role = 'admin' (default)
    op.execute("""
        UPDATE users 
        SET role = COALESCE(
            (SELECT name FROM roles WHERE roles.id = users.role_id), 
            'admin'
        )
    """)
    
    # Make role column NOT NULL after data migration
    op.alter_column('users', 'role', nullable=False, server_default='admin')


def downgrade() -> None:
    """Downgrade schema."""
    # Remove role column
    op.drop_column('users', 'role')
