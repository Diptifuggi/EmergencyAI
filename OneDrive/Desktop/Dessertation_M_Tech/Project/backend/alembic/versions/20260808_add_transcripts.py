"""Add persistent Flutter STT transcripts.

Revision ID: 20260808_add_transcripts
Revises:
Create Date: 2026-08-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260808_add_transcripts"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_index("ix_transcripts_user_id", table_name="transcripts")
    op.drop_index("ix_transcripts_created_at", table_name="transcripts")
    op.drop_table("transcripts")
