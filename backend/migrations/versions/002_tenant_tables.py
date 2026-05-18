"""Add Tenant, TenantUser, TenantData, Department, SessionProfile tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("subscription_tier", sa.Enum("basic", "standard", "advanced", "flagship", name="subscription_tier"), nullable=False, server_default="basic"),
        sa.Column("status", sa.Enum("active", "suspended", "cancelled", name="tenant_status"), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_tenants_slug", "tenants", ["slug"])

    op.create_table(
        "tenant_users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.Enum("admin", "manager", "viewer", "department_head", name="tenant_user_role"), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_tenant_users_tenant", "tenant_users", ["tenant_id"])

    op.create_table(
        "tenant_data",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("data_type", sa.Enum("admission_score", "curriculum", "employment", "campus_life", name="tenant_data_type"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", JSONB, nullable=False, server_default="{}"),
        sa.Column("source_url", sa.String(1000), server_default=""),
        sa.Column("year", sa.Integer),
        sa.Column("province", sa.String(100)),
        sa.Column("extra_meta", JSONB, server_default="{}"),
        sa.Column("indexed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_tenant_data_tenant", "tenant_data", ["tenant_id"])

    op.create_table(
        "departments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("config", JSONB, server_default="{}"),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("departments.id"), nullable=True),
    )
    op.create_index("idx_departments_tenant", "departments", ["tenant_id"])

    op.create_table(
        "session_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("profile_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("completeness", sa.String(10)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_session_profiles_tenant", "session_profiles", ["tenant_id"])
    op.create_index("idx_session_profiles_session", "session_profiles", ["session_id"])


def downgrade() -> None:
    op.drop_table("session_profiles")
    op.drop_table("departments")
    op.drop_table("tenant_data")
    op.drop_table("tenant_users")
    op.drop_table("tenants")
    # Clean up enums
    op.execute("DROP TYPE IF EXISTS tenant_user_role")
    op.execute("DROP TYPE IF EXISTS tenant_data_type")
    op.execute("DROP TYPE IF EXISTS tenant_status")
    op.execute("DROP TYPE IF EXISTS subscription_tier")
