"""Persist an automatic location-capture status for emergency calls.

Revision ID: 20260831_add_location_status
Revises: 20260831_add_postgis_geometry
"""

from alembic import op
import sqlalchemy as sa


revision = "20260831_add_location_status"
down_revision = "20260831_add_postgis_geometry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}

    if "location_status" not in columns:
        op.add_column(
            "emergency_calls",
            sa.Column(
                "location_status",
                sa.String(length=20),
                nullable=False,
                server_default="unavailable",
            ),
        )

    # Keep the value correct even for SQL written outside this API.
    op.execute("""
        CREATE OR REPLACE FUNCTION update_emergency_location_status()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
                NEW.location_status := 'captured';
            ELSE
                NEW.location_status := 'unavailable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("DROP TRIGGER IF EXISTS trg_update_emergency_location_status ON emergency_calls;")
    op.execute("""
        CREATE TRIGGER trg_update_emergency_location_status
        BEFORE INSERT OR UPDATE OF latitude, longitude ON emergency_calls
        FOR EACH ROW
        EXECUTE FUNCTION update_emergency_location_status();
    """)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}
    op.execute("DROP TRIGGER IF EXISTS trg_update_emergency_location_status ON emergency_calls;")
    op.execute("DROP FUNCTION IF EXISTS update_emergency_location_status();")
    if "location_status" in columns:
        op.drop_column("emergency_calls", "location_status")
