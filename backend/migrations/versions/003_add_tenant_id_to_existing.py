"""Add tenant_id column to all existing user/data tables

Revision ID: 003
Revises: 002
Create Date: 2026-05-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels = None
depends_on = None

TABLES = [
    "users",
    "colleges",
    "admission_data",
    "user_profiles",
    "recommendations",
    "recommendation_feedback",
]


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("tenant_id", UUID(as_uuid=True), nullable=True))
        op.create_index(f"idx_{table}_tenant", table, ["tenant_id"])

    # Also add user_type to users
    op.add_column("users", sa.Column("user_type", sa.String(20), server_default="student"))


def downgrade() -> None:
    op.drop_column("users", "user_type")
    for table in TABLES:
        op.drop_index(f"idx_{table}_tenant", table_name=table)
        op.drop_column(table, "tenant_id")
