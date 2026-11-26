"""Add SOS alerts, user profiles, location updates, events, and profile access log.

Revision ID: 20261124_sos_and_profiles
Revises: 20261027_location_address_status
Create Date: 2026-11-24
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20261124_sos_and_profiles'
down_revision: Union[str, None] = '20261027_location_address_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. user_profiles
    if "user_profiles" not in existing_tables:
        op.create_table(
            "user_profiles",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column("full_name", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=20), nullable=True),
            sa.Column("alternate_phone", sa.String(length=20), nullable=True),
            sa.Column("guardian_phone", sa.String(length=20), nullable=True),
            sa.Column("guardian_relation", sa.String(length=50), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("age", sa.Integer(), nullable=True),
            sa.Column("blood_group", sa.String(length=20), nullable=True, server_default="unknown"),
            sa.Column("allergies", sa.Text(), nullable=True),
            sa.Column("medical_history", sa.Text(), nullable=True),
            sa.Column("medical_consent", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("medical_consent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("profile_completed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"])

    # 2. sos_alerts
    if "sos_alerts" not in existing_tables:
        op.create_table(
            "sos_alerts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False, unique=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("alert_type", sa.String(length=30), nullable=False),
            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("accuracy_m", sa.Float(), nullable=True),
            sa.Column(
                "location_status",
                sa.String(length=30),
                nullable=False,
                server_default="unavailable",
            ),
            sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "received_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("battery_pct", sa.Integer(), nullable=True),
            sa.Column("network_type", sa.String(length=50), nullable=True),
            sa.Column("device_id", sa.String(length=128), nullable=True),
            sa.Column("app_version", sa.String(length=50), nullable=True),
            sa.Column("profile_snapshot_encrypted", sa.Text(), nullable=True),
            sa.Column(
                "acknowledged_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancel_reason", sa.Text(), nullable=True),
            sa.Column("close_reason", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_sos_alerts_status", "sos_alerts", ["status"])
        op.create_index("ix_sos_alerts_received_at", "sos_alerts", ["received_at"])
        op.create_index("ix_sos_alerts_user_id", "sos_alerts", ["user_id"])
        op.create_index("ix_sos_alerts_alert_type", "sos_alerts", ["alert_type"])
        op.create_index("ix_sos_alerts_idempotency_key", "sos_alerts", ["idempotency_key"])

    # 3. sos_location_updates
    if "sos_location_updates" not in existing_tables:
        op.create_table(
            "sos_location_updates",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "alert_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("sos_alerts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("accuracy_m", sa.Float(), nullable=True),
            sa.Column(
                "recorded_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_sos_location_updates_alert_id", "sos_location_updates", ["alert_id"])

    # 4. sos_events
    if "sos_events" not in existing_tables:
        op.create_table(
            "sos_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "alert_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("sos_alerts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("actor_type", sa.String(length=20), nullable=False),
            sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_sos_events_alert_id", "sos_events", ["alert_id"])

    # 5. sos_profile_access_log
    if "sos_profile_access_log" not in existing_tables:
        op.create_table(
            "sos_profile_access_log",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "alert_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("sos_alerts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "operator_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "accessed_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_sos_profile_access_log_alert_id", "sos_profile_access_log", ["alert_id"])
        op.create_index("ix_sos_profile_access_log_operator_id", "sos_profile_access_log", ["operator_id"])


def downgrade() -> None:
    op.drop_table("sos_profile_access_log")
    op.drop_table("sos_events")
    op.drop_table("sos_location_updates")
    op.drop_table("sos_alerts")
    op.drop_table("user_profiles")
