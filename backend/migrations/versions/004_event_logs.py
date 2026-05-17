"""Add event_logs table (partitioned by month)

Revision ID: 004
Revises: 003
Create Date: 2026-05-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE event_logs (
            id UUID DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            event_type VARCHAR(64) NOT NULL,
            user_id UUID,
            session_id UUID,
            payload JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        ) PARTITION BY RANGE (created_at)
    """)
    # Initial partitions
    op.execute("""
        CREATE TABLE event_logs_2026_05 PARTITION OF event_logs
            FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
    """)
    op.execute("""
        CREATE TABLE event_logs_2026_06 PARTITION OF event_logs
            FOR VALUES FROM ('2026-06-01') TO ('2026-07-01')
    """)
    op.create_index("idx_event_logs_tenant_time", "event_logs", ["tenant_id", sa.text("created_at DESC")])
    op.create_index("idx_event_logs_type_tenant", "event_logs", ["event_type", "tenant_id", sa.text("created_at DESC")])
    op.create_index("idx_event_logs_session", "event_logs", ["session_id", sa.text("created_at")])


def downgrade() -> None:
    op.drop_table("event_logs")
