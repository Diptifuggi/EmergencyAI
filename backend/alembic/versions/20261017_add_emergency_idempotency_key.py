"""Add an optional unique retry key to emergency calls.

Revision ID: 20261017_emergency_retry
Revises: 20260901_add_map_snapshot, 9aa729b7585c
"""

from alembic import op
import sqlalchemy as sa


revision = "20261017_emergency_retry"
down_revision = ("20260901_add_map_snapshot", "9aa729b7585c")
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}
    if "idempotency_key" not in columns:
        op.add_column(
            "emergency_calls",
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        )

    indexes = {index["name"] for index in inspector.get_indexes("emergency_calls")}
    if "uq_emergency_calls_idempotency_key" not in indexes:
        op.create_index(
            "uq_emergency_calls_idempotency_key",
            "emergency_calls",
            ["idempotency_key"],
            unique=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = {index["name"] for index in inspector.get_indexes("emergency_calls")}
    if "uq_emergency_calls_idempotency_key" in indexes:
        op.drop_index("uq_emergency_calls_idempotency_key", table_name="emergency_calls")
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}
    if "idempotency_key" in columns:
        op.drop_column("emergency_calls", "idempotency_key")