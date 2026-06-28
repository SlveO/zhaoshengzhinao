"""consult workbench: add 8 fields + backfill consult_started_at

Revision ID: 008_consult_workbench
Revises: 007_db_admin_panel
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "008_consult_workbench"
down_revision = "007_db_admin_panel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: only add if column missing (tolerant of partial applies)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("consult_sessions")}

    if "subjects" not in existing_cols:
        op.add_column("consult_sessions", sa.Column("subjects", sa.String(20), server_default="", nullable=False))
    if "rank" not in existing_cols:
        op.add_column("consult_sessions", sa.Column("rank", sa.Integer(), nullable=True))
    if "consult_summary" not in existing_cols:
        op.add_column("consult_sessions", sa.Column("consult_summary", sa.Text(), nullable=True))
    if "consult_started_at" not in existing_cols:
        op.add_column("consult_sessions", sa.Column("consult_started_at", sa.DateTime(timezone=True), nullable=True))
    if "follow_status" not in existing_cols:
        op.add_column("consult_sessions", sa.Column("follow_status", sa.String(20), server_default="pending", nullable=False))
    if "follow_note" not in existing_cols:
        op.add_column("consult_sessions", sa.Column("follow_note", sa.Text(), nullable=True))
    if "followed_at" not in existing_cols:
        op.add_column("consult_sessions", sa.Column("followed_at", sa.DateTime(timezone=True), nullable=True))
    if "followed_by" not in existing_cols:
        op.add_column("consult_sessions", sa.Column("followed_by", postgresql.UUID(as_uuid=True), nullable=True))

    # Backfill consult_started_at from first user message
    op.execute("""
        UPDATE consult_sessions cs
        SET consult_started_at = (
          SELECT MIN(created_at) FROM chat_messages cm
          WHERE cm.session_id = cs.session_id AND cm.role = 'user'
        )
        WHERE cs.consult_started_at IS NULL
          AND EXISTS (
            SELECT 1 FROM chat_messages cm
            WHERE cm.session_id = cs.session_id AND cm.role = 'user'
          )
    """)


def downgrade() -> None:
    for col in ["followed_by", "followed_at", "follow_note", "follow_status",
                "consult_started_at", "consult_summary", "rank", "subjects"]:
        op.drop_column("consult_sessions", col)
