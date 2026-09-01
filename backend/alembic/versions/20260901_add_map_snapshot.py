"""Add nullable map snapshot metadata to emergency calls.

Revision ID: 20260901_add_map_snapshot
Revises: 20260831_add_location_status
"""

from alembic import op
import sqlalchemy as sa


revision = "20260901_add_map_snapshot"
down_revision = "20260831_add_location_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}
    additions = [
        sa.Column("map_snapshot_file_path", sa.String(length=260), nullable=True),
        sa.Column("map_snapshot_filename", sa.String(length=260), nullable=True),
        sa.Column("map_snapshot_content_type", sa.String(length=100), nullable=True),
        sa.Column("map_snapshot_size", sa.Integer(), nullable=True),
        sa.Column("map_snapshot_url", sa.String(length=500), nullable=True),
    ]
    for column in additions:
        if column.name not in columns:
            op.add_column("emergency_calls", column)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}
    for name in (
        "map_snapshot_url",
        "map_snapshot_size",
        "map_snapshot_content_type",
        "map_snapshot_filename",
        "map_snapshot_file_path",
    ):
        if name in columns:
            op.drop_column("emergency_calls", name)
