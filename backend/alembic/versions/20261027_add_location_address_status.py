"""Track reverse-geocoding independently from GPS capture.

Revision ID: 20261027_location_address_status
Revises: 20261017_emergency_retry
"""

from alembic import op
import sqlalchemy as sa


revision = "20261027_location_address_status"
down_revision = "20261017_emergency_retry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}
    if "location_address_status" not in columns:
        op.add_column(
            "emergency_calls",
            sa.Column(
                "location_address_status",
                sa.String(length=20),
                nullable=False,
                server_default="unavailable",
            ),
        )

    op.execute(
        """
        UPDATE emergency_calls
        SET location_address_status = CASE
            WHEN location_address IS NOT NULL AND btrim(location_address) <> '' THEN 'unknown'
            WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 'failed'
            ELSE 'unavailable'
        END
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}
    if "location_address_status" in columns:
        op.drop_column("emergency_calls", "location_address_status")
