"""Add emergency_calls table.

Revision ID: 20260810_add_emergency_calls
Revises: 20260808_add_transcripts
Create Date: 2026-08-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260810_add_emergency_calls"
down_revision = "20260808_add_transcripts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emergency_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("call_type", sa.String(length=20), nullable=False, server_default="text"),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=35), nullable=True),
        sa.Column("status", sa.String(length=35), nullable=False, server_default="received"),
        sa.Column("priority", sa.String(length=35), nullable=False, server_default="normal"),
        sa.Column("audio_file_path", sa.String(length=260), nullable=True),
        sa.Column("original_audio_filename", sa.String(length=260), nullable=True),
        sa.Column("audio_content_type", sa.String(length=100), nullable=True),
        sa.Column("audio_file_size", sa.Integer(), nullable=True),
        sa.Column("transcription", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emergency_calls_created_at", "emergency_calls", ["created_at"])
    op.create_index("ix_emergency_calls_status", "emergency_calls", ["status"])


def downgrade() -> None:
    op.drop_index("ix_emergency_calls_status", table_name="emergency_calls")
    op.drop_index("ix_emergency_calls_created_at", table_name="emergency_calls")
    op.drop_table("emergency_calls")
