"""Add service_category to sos_alerts and emergency_contacts, user_notifications, track_sessions, track_points.

Revision ID: 20261126_home_features
Revises: 20261124_sos_and_profiles
Create Date: 2026-11-26
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '20261126_home_features'
down_revision: Union[str, None] = '20261124_sos_and_profiles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Extend sos_alerts with service_category and category_source
    if "sos_alerts" in existing_tables:
        sos_cols = {c["name"] for c in inspector.get_columns("sos_alerts")}
        if "service_category" not in sos_cols:
            op.add_column(
                "sos_alerts",
                sa.Column(
                    "service_category",
                    sa.String(length=30),
                    nullable=True,
                    server_default="general",
                ),
            )
            op.create_index(
                "ix_sos_alerts_service_category",
                "sos_alerts",
                ["service_category"],
            )
        if "category_source" not in sos_cols:
            op.add_column(
                "sos_alerts",
                sa.Column(
                    "category_source",
                    sa.String(length=30),
                    nullable=True,
                    server_default="user_selected",
                ),
            )

    # 2. emergency_contacts
    if "emergency_contacts" not in existing_tables:
        op.create_table(
            "emergency_contacts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=20), nullable=False),
            sa.Column("relation", sa.String(length=50), nullable=False),
            sa.Column("notify_on_sos", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
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
        op.create_index("ix_emergency_contacts_user_id", "emergency_contacts", ["user_id"])

    # 3. user_notifications
    if "user_notifications" not in existing_tables:
        op.create_table(
            "user_notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "alert_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("sos_alerts.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("notification_type", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_user_notifications_user_id", "user_notifications", ["user_id"])
        op.create_index("ix_user_notifications_alert_id", "user_notifications", ["alert_id"])
        op.create_index("ix_user_notifications_is_read", "user_notifications", ["is_read"])
        op.create_index("ix_user_notifications_created_at", "user_notifications", ["created_at"])

    # 4. track_sessions
    if "track_sessions" not in existing_tables:
        op.create_table(
            "track_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("share_token", sa.String(length=128), nullable=False, unique=True),
            sa.Column("duration_hours", sa.Integer(), nullable=False),
            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default="active",
            ),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_track_sessions_user_id", "track_sessions", ["user_id"])
        op.create_index("ix_track_sessions_share_token", "track_sessions", ["share_token"], unique=True)
        op.create_index("ix_track_sessions_status", "track_sessions", ["status"])
        op.create_index("ix_track_sessions_expires_at", "track_sessions", ["expires_at"])

    # 5. track_points
    if "track_points" not in existing_tables:
        op.create_table(
            "track_points",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "session_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("track_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("accuracy_m", sa.Float(), nullable=True),
            sa.Column("battery_pct", sa.Integer(), nullable=True),
            sa.Column(
                "recorded_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_track_points_session_id", "track_points", ["session_id"])
        op.create_index("ix_track_points_recorded_at", "track_points", ["recorded_at"])


def downgrade() -> None:
    op.drop_table("track_points")
    op.drop_table("track_sessions")
    op.drop_table("user_notifications")
    op.drop_table("emergency_contacts")
    op.drop_index("ix_sos_alerts_service_category", table_name="sos_alerts")
    op.drop_column("sos_alerts", "category_source")
    op.drop_column("sos_alerts", "service_category")
