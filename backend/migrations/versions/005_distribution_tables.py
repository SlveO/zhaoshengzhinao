"""Add distribution tables: channels, files, tasks, logs, access tokens

Revision ID: 005
Revises: 004
Create Date: 2026-06-05
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── distribution_channels ──
    op.create_table(
        "distribution_channels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("channel_type", sa.Enum("wechat_group", name="distribution_channel_type"), nullable=False, server_default="wechat_group"),
        sa.Column("webhook_url", sa.Text, nullable=False),
        sa.Column("config", JSONB, server_default="{}"),
        sa.Column("status", sa.Enum("active", "inactive", "error", name="distribution_channel_status"), server_default="active"),
        sa.Column("last_test_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_distribution_channels_tenant", "distribution_channels", ["tenant_id"])

    # ── distribution_files ──
    op.create_table(
        "distribution_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("stored_path", sa.String(1000), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("file_hash", sa.String(64)),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("tenant_users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_distribution_files_tenant", "distribution_files", ["tenant_id"])

    # ── distribution_tasks ──
    op.create_table(
        "distribution_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("file_id", UUID(as_uuid=True), sa.ForeignKey("distribution_files.id"), nullable=False),
        sa.Column("channel_id", UUID(as_uuid=True), sa.ForeignKey("distribution_channels.id"), nullable=False),
        sa.Column("schedule_type", sa.Enum("once", "daily", "weekly", "monthly", name="distribution_schedule_type"), server_default="once"),
        sa.Column("schedule_config", JSONB, server_default="{}"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Enum("draft", "active", "paused", "completed", "failed", name="distribution_task_status"), server_default="draft"),
        sa.Column("message_text", sa.Text),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("tenant_users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_distribution_tasks_tenant", "distribution_tasks", ["tenant_id"])
    op.create_index("idx_distribution_tasks_status_scheduled", "distribution_tasks", ["status", "scheduled_at"])

    # ── distribution_logs ──
    op.create_table(
        "distribution_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("distribution_tasks.id"), nullable=False),
        sa.Column("channel_id", UUID(as_uuid=True), sa.ForeignKey("distribution_channels.id"), nullable=False),
        sa.Column("file_id", UUID(as_uuid=True), sa.ForeignKey("distribution_files.id"), nullable=False),
        sa.Column("status", sa.Enum("pending", "sending", "success", "failed", name="distribution_log_status"), server_default="pending"),
        sa.Column("attempt", sa.Integer, server_default="1"),
        sa.Column("request_payload", JSONB),
        sa.Column("response_body", JSONB),
        sa.Column("error_message", sa.Text),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_distribution_logs_tenant", "distribution_logs", ["tenant_id"])
    op.create_index("idx_distribution_logs_task", "distribution_logs", ["task_id"])

    # ── distribution_file_access_tokens ──
    op.create_table(
        "distribution_file_access_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("file_id", UUID(as_uuid=True), sa.ForeignKey("distribution_files.id"), nullable=False),
        sa.Column("token", sa.String(128), unique=True, nullable=False),
        sa.Column("channel_id", UUID(as_uuid=True), sa.ForeignKey("distribution_channels.id"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("access_count", sa.Integer, server_default="0"),
        sa.Column("max_access", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_distribution_access_tokens_file", "distribution_file_access_tokens", ["file_id"])


def downgrade() -> None:
    op.drop_table("distribution_file_access_tokens")
    op.drop_table("distribution_logs")
    op.drop_table("distribution_tasks")
    op.drop_table("distribution_files")
    op.drop_table("distribution_channels")
    # Clean up enums
    op.execute("DROP TYPE IF EXISTS distribution_log_status")
    op.execute("DROP TYPE IF EXISTS distribution_task_status")
    op.execute("DROP TYPE IF EXISTS distribution_schedule_type")
    op.execute("DROP TYPE IF EXISTS distribution_channel_status")
    op.execute("DROP TYPE IF EXISTS distribution_channel_type")
