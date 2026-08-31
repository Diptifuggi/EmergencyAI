"""Add optional emergency location metadata.

Revision ID: 20260827_add_location_metadata
Revises: 20260811_voice_text_ext
"""

from alembic import op
import sqlalchemy as sa


revision = "20260827_add_location_metadata"
down_revision = "20260811_voice_text_ext"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}
    additions = {
        "location_accuracy": sa.Column("location_accuracy", sa.Float(), nullable=True),
        "location_timestamp": sa.Column(
            "location_timestamp", sa.DateTime(timezone=True), nullable=True
        ),
        "location_address": sa.Column("location_address", sa.Text(), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("emergency_calls", column)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}
    for name in ("location_address", "location_timestamp", "location_accuracy"):
        if name in columns:
            op.drop_column("emergency_calls", name)