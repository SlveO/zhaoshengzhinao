"""add consult_sessions and chat_messages tables

Revision ID: 005
Revises: 004
Create Date: 2026-05-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consult_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("tenant_slug", sa.String(50), nullable=False, server_default="scnu"),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("province", sa.String(50), server_default=""),
        sa.Column("subject_type", sa.String(20), server_default=""),
        sa.Column("score", sa.Integer, server_default="0"),
        sa.Column("intent_majors", JSONB, server_default="[]"),
        sa.Column("focus_points", JSONB, server_default="[]"),
        sa.Column("consult_stage", sa.String(30), server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.String(100), nullable=False, index=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.add_column("recommendations", sa.Column("session_id", sa.String(100), nullable=True))
    op.create_index("ix_recommendations_session_id", "recommendations", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_recommendations_session_id", "recommendations")
    op.drop_column("recommendations", "session_id")
    op.drop_table("chat_messages")
    op.drop_table("consult_sessions")
