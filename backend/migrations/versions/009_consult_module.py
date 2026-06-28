"""consult module: prompt_templates table + consult_sessions.context_ref_session_id

Revision ID: 009_consult_module
Revises: 008_consult_workbench
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "009_consult_module"
down_revision = "008_consult_workbench"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. 新增 prompt_templates 表（幂等：init_db.create_all 可能已创建）
    if "prompt_templates" not in existing_tables:
        op.create_table(
            "prompt_templates",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_slug", sa.String(50), nullable=False, server_default="scnu"),
            sa.Column("prompt_key", sa.String(50), nullable=False),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("version", sa.Integer, nullable=False, server_default="1"),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.clock_timestamp()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("tenant_slug", "prompt_key", "version", name="uq_prompt_version"),
        )
        op.create_index("ix_prompt_templates_tenant_slug", "prompt_templates", ["tenant_slug"])
        op.create_index("ix_prompt_templates_prompt_key", "prompt_templates", ["prompt_key"])
        op.create_index("ix_prompt_templates_is_active", "prompt_templates", ["is_active"])
    else:
        # 表已存在，仅补建缺失的索引（幂等）
        existing_indexes = {ix["name"] for ix in inspector.get_indexes("prompt_templates")}
        if "ix_prompt_templates_tenant_slug" not in existing_indexes:
            op.create_index("ix_prompt_templates_tenant_slug", "prompt_templates", ["tenant_slug"])
        if "ix_prompt_templates_prompt_key" not in existing_indexes:
            op.create_index("ix_prompt_templates_prompt_key", "prompt_templates", ["prompt_key"])
        if "ix_prompt_templates_is_active" not in existing_indexes:
            op.create_index("ix_prompt_templates_is_active", "prompt_templates", ["is_active"])

    # 2. consult_sessions 新增 context_ref_session_id（幂等）
    existing_cols = {c["name"] for c in inspector.get_columns("consult_sessions")}
    if "context_ref_session_id" not in existing_cols:
        op.add_column(
            "consult_sessions",
            sa.Column("context_ref_session_id", postgresql.UUID(as_uuid=True), nullable=True)
        )
        op.create_index(
            "ix_consult_sessions_context_ref",
            "consult_sessions",
            ["context_ref_session_id"]
        )


def downgrade() -> None:
    op.drop_index("ix_consult_sessions_context_ref", table_name="consult_sessions")
    op.drop_column("consult_sessions", "context_ref_session_id")
    op.drop_index("ix_prompt_templates_is_active", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_prompt_key", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_tenant_slug", table_name="prompt_templates")
    op.drop_table("prompt_templates")
