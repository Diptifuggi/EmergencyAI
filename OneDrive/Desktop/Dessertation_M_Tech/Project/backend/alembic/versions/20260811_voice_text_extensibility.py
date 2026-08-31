"""Ensure transcripts table and extensible emergency_calls columns.

Revision ID: 20260811_voice_text_ext
Revises: 20260810_add_emergency_calls
Create Date: 2026-08-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260811_voice_text_ext"
down_revision = "20260810_add_emergency_calls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names(schema="public"))

    if "transcripts" not in tables:
        op.create_table(
            "transcripts",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("transcript_text", sa.Text(), nullable=False),
            sa.Column("language", sa.String(length=35), nullable=False),
            sa.Column("source", sa.String(length=50), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_transcripts_created_at", "transcripts", ["created_at"])
        op.create_index("ix_transcripts_user_id", "transcripts", ["user_id"])

    emergency_cols = {
        col["name"] for col in inspector.get_columns("emergency_calls", schema="public")
    }

    if "source" not in emergency_cols:
        op.add_column(
            "emergency_calls",
            sa.Column("source", sa.String(length=50), nullable=True, server_default="flutter"),
        )

    if "client_metadata" not in emergency_cols:
        op.add_column(
            "emergency_calls",
            sa.Column(
                "client_metadata",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )

    if "audio_url" not in emergency_cols:
        op.add_column(
            "emergency_calls",
            sa.Column("audio_url", sa.String(length=500), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    emergency_cols = {
        col["name"] for col in inspector.get_columns("emergency_calls", schema="public")
    }

    if "audio_url" in emergency_cols:
        op.drop_column("emergency_calls", "audio_url")
    if "client_metadata" in emergency_cols:
        op.drop_column("emergency_calls", "client_metadata")
    if "source" in emergency_cols:
        op.drop_column("emergency_calls", "source")

    tables = set(inspector.get_table_names(schema="public"))
    if "transcripts" in tables:
        op.drop_index("ix_transcripts_user_id", table_name="transcripts")
        op.drop_index("ix_transcripts_created_at", table_name="transcripts")
        op.drop_table("transcripts")
