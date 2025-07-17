"""remove_organization_and_role_tables

Revision ID: e38c9097fa22
Revises: 9b9d11e4c56a
Create Date: 2025-07-17 09:39:20.543696

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e38c9097fa22'
down_revision: Union[str, Sequence[str], None] = '9b9d11e4c56a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop foreign key constraints first
    op.drop_constraint('users_role_id_fkey', 'users', type_='foreignkey')
    op.drop_constraint('users_organization_id_fkey', 'users', type_='foreignkey')
    op.drop_constraint('vehicles_organization_id_fkey', 'vehicles', type_='foreignkey')
    op.drop_constraint('drivers_organization_id_fkey', 'drivers', type_='foreignkey')
    
    # Drop columns from users table
    op.drop_column('users', 'role_id')
    op.drop_column('users', 'organization_id')
    
    # Drop columns from vehicles table
    op.drop_column('vehicles', 'organization_id')
    
    # Drop columns from drivers table
    op.drop_column('drivers', 'organization_id')
    
    # Drop tables
    op.drop_table('roles')
    op.drop_table('organizations')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate tables (this is complex, mainly for reference)
    op.create_table('organizations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('tax_code', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('roles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Add back columns
    op.add_column('users', sa.Column('organization_id', sa.UUID(), nullable=True))
    op.add_column('users', sa.Column('role_id', sa.UUID(), nullable=True))
    op.add_column('vehicles', sa.Column('organization_id', sa.UUID(), nullable=True))
    op.add_column('drivers', sa.Column('organization_id', sa.UUID(), nullable=True))
    
    # Add back foreign keys
    op.create_foreign_key('users_organization_id_fkey', 'users', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('users_role_id_fkey', 'users', 'roles', ['role_id'], ['id'])
    op.create_foreign_key('vehicles_organization_id_fkey', 'vehicles', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('drivers_organization_id_fkey', 'drivers', 'organizations', ['organization_id'], ['id'])
