"""Refactor: Remove Vehicle, update Device, Driver, JourneySession

Revision ID: cdb60e15e44b
Revises: 7ebd02b5f8f1
Create Date: 2025-10-02 11:54:50.148195

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cdb60e15e44b'
down_revision: Union[str, Sequence[str], None] = '7ebd02b5f8f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with data migration."""
    # Phase 1: Add new columns as nullable
    op.add_column('devices', sa.Column('device_name', sa.String(length=100), nullable=True))
    op.add_column('devices', sa.Column('device_type', sa.String(length=50), nullable=True))
    op.add_column('devices', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('journey_sessions', sa.Column('device_id', sa.UUID(), nullable=True))
    op.add_column('images', sa.Column('device_id', sa.UUID(), nullable=True))
    op.add_column('alerts', sa.Column('device_id', sa.UUID(), nullable=True))

    # Phase 2: Data Migration
    # Migrate vehicle info to devices
    op.execute("""
        UPDATE devices
        SET device_name = v.plate_number,
            device_type = v.type,
            description = CONCAT('Load capacity: ', v.load_capacity_kg, 'kg')
        FROM vehicles v
        WHERE devices.vehicle_id = v.id;
    """)

    # Migrate journey_sessions to use device_id
    op.execute("""
        UPDATE journey_sessions
        SET device_id = d.id
        FROM devices d
        WHERE d.vehicle_id = journey_sessions.vehicle_id;
    """)

    # Migrate images to use device_id
    op.execute("""
        UPDATE images
        SET device_id = d.id
        FROM devices d
        WHERE d.vehicle_id = images.vehicle_id;
    """)

    # Migrate alerts to use device_id
    op.execute("""
        UPDATE alerts
        SET device_id = d.id
        FROM devices d
        WHERE d.vehicle_id = alerts.vehicle_id;
    """)

    # Phase 3: Clean up orphaned records and add NOT NULL constraints
    op.execute('DELETE FROM journey_sessions WHERE device_id IS NULL')
    op.execute('DELETE FROM images WHERE device_id IS NULL')
    op.execute('DELETE FROM alerts WHERE device_id IS NULL')
    op.alter_column('journey_sessions', 'device_id', nullable=False)
    op.alter_column('images', 'device_id', nullable=False)
    op.alter_column('alerts', 'device_id', nullable=False)

    # Phase 4: Cleanup old schema
    # Drop foreign keys pointing to vehicles
    op.drop_constraint('devices_vehicle_id_fkey', 'devices', type_='foreignkey')
    op.drop_constraint('journey_sessions_vehicle_id_fkey', 'journey_sessions', type_='foreignkey')
    op.drop_constraint('images_vehicle_id_fkey', 'images', type_='foreignkey')
    op.drop_constraint('alerts_vehicle_id_fkey', 'alerts', type_='foreignkey')

    # Drop unique constraint on devices.vehicle_id
    op.drop_constraint('devices_vehicle_id_key', 'devices', type_='unique')

    # Drop old columns
    op.drop_column('devices', 'vehicle_id')
    op.drop_column('journey_sessions', 'vehicle_id')
    op.drop_column('images', 'vehicle_id')
    op.drop_column('alerts', 'vehicle_id')
    # The columns 'license_number' and 'card_id' might have been dropped in a previous failed attempt.
    # We will skip dropping them again to avoid errors.

    # Foreign keys might have been created in a previous failed attempt.
    # We will skip creating them again to avoid errors.

    # Drop old columns - the associated indexes will be dropped automatically
    op.drop_column('drivers', 'license_number')
    op.drop_column('drivers', 'card_id')

    # Create new foreign keys to devices
    op.create_foreign_key('fk_journey_sessions_device_id', 'journey_sessions', 'devices', ['device_id'], ['id'])
    op.create_foreign_key('fk_images_device_id', 'images', 'devices', ['device_id'], ['id'])
    op.create_foreign_key('fk_alerts_device_id', 'alerts', 'devices', ['device_id'], ['id'])

    # Finally, drop the obsolete tables. Their indexes will be dropped with them.
    op.drop_table('vehicles')
    op.drop_table('locations')


def downgrade() -> None:
    """Downgrade schema (reverts the refactor)."""
    # This is complex and data loss is possible. Best effort.

    # Re-create vehicles table
    op.create_table('vehicles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('plate_number', sa.VARCHAR(length=20), nullable=False),
        sa.Column('type', sa.VARCHAR(length=50), nullable=True),
        sa.Column('load_capacity_kg', sa.INTEGER(), nullable=True),
        sa.Column('registration_expiry', sa.DATE(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id', name='vehicles_pkey')
    )
    op.create_index('ix_vehicles_plate_number', 'vehicles', ['plate_number'], unique=True)

    # Add back columns
    op.add_column('drivers', sa.Column('card_id', sa.VARCHAR(length=50), nullable=True))
    op.add_column('drivers', sa.Column('license_number', sa.VARCHAR(length=50), nullable=True))
    op.add_column('devices', sa.Column('vehicle_id', sa.UUID(), nullable=True))
    op.add_column('journey_sessions', sa.Column('vehicle_id', sa.UUID(), nullable=True))
    op.add_column('images', sa.Column('vehicle_id', sa.UUID(), nullable=True))
    op.add_column('alerts', sa.Column('vehicle_id', sa.UUID(), nullable=True))

    # Data migration (reverse) - very basic, might not be perfect
    op.execute("""
        INSERT INTO vehicles (id, plate_number, type, created_at)
        SELECT id, device_name, device_type, created_at FROM devices
        ON CONFLICT (id) DO NOTHING;
    """)
    op.execute('UPDATE devices SET vehicle_id = id;')
    op.execute('UPDATE journey_sessions SET vehicle_id = device_id;')
    op.execute('UPDATE images SET vehicle_id = device_id;')
    op.execute('UPDATE alerts SET vehicle_id = device_id;')

    # Make columns non-nullable after data migration
    op.alter_column('drivers', 'license_number', nullable=False)
    op.alter_column('journey_sessions', 'vehicle_id', nullable=False)
    op.alter_column('images', 'vehicle_id', nullable=False)
    op.alter_column('alerts', 'vehicle_id', nullable=False)

    # Drop new columns and foreign keys
    op.drop_constraint('fk_journey_sessions_device_id', 'journey_sessions', type_='foreignkey')
    op.drop_constraint('fk_images_device_id', 'images', type_='foreignkey')
    op.drop_constraint('fk_alerts_device_id', 'alerts', type_='foreignkey')
    op.drop_column('journey_sessions', 'device_id')
    op.drop_column('images', 'device_id')
    op.drop_column('alerts', 'device_id')
    op.drop_column('devices', 'description')
    op.drop_column('devices', 'device_type')
    op.drop_column('devices', 'device_name')

    # Recreate old foreign keys and constraints
    op.create_foreign_key('devices_vehicle_id_fkey', 'devices', 'vehicles', ['vehicle_id'], ['id'])
    op.create_unique_constraint('devices_vehicle_id_key', 'devices', ['vehicle_id'])
    op.create_foreign_key('journey_sessions_vehicle_id_fkey', 'journey_sessions', 'vehicles', ['vehicle_id'], ['id'])
    op.create_foreign_key('images_vehicle_id_fkey', 'images', 'vehicles', ['vehicle_id'], ['id'])
    op.create_foreign_key('alerts_vehicle_id_fkey', 'alerts', 'vehicles', ['vehicle_id'], ['id'])
    op.create_index('ix_drivers_license_number', 'drivers', ['license_number'], unique=True)
    op.create_index('ix_drivers_card_id', 'drivers', ['card_id'], unique=True)
