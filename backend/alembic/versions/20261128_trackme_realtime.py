"""Add TrackMe control room toggle, SOS link, and client_point_id deduplication.

Revision ID: 20261128_trackme_realtime
Revises: 20261128_auth_and_audit
Create Date: 2026-11-28
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '20261128_trackme_realtime'
down_revision: Union[str, None] = '20261128_auth_and_audit'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "track_sessions" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("track_sessions")}
        if "share_with_control_room" not in cols:
            op.add_column(
                "track_sessions",
                sa.Column("share_with_control_room", sa.Boolean(), nullable=False, server_default="false"),
            )
        if "sos_alert_id" not in cols:
            op.add_column(
                "track_sessions",
                sa.Column(
                    "sos_alert_id",
                    postgresql.UUID(as_uuid=True),
                    sa.ForeignKey("sos_alerts.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )
            op.create_index("ix_track_sessions_sos_alert_id", "track_sessions", ["sos_alert_id"])

    if "track_points" in existing_tables:
        pcols = {c["name"] for c in inspector.get_columns("track_points")}
        if "client_point_id" not in pcols:
            op.add_column(
                "track_points",
                sa.Column("client_point_id", sa.String(length=64), nullable=True),
            )
            op.create_unique_constraint(
                "uq_track_point_client_id",
                "track_points",
                ["session_id", "client_point_id"],
            )


def downgrade() -> None:
    op.drop_constraint("uq_track_point_client_id", "track_points", type_="unique")
    op.drop_column("track_points", "client_point_id")
    op.drop_index("ix_track_sessions_sos_alert_id", table_name="track_sessions")
    op.drop_column("track_sessions", "sos_alert_id")
    op.drop_column("track_sessions", "share_with_control_room")
