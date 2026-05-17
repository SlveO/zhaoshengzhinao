"""Initial schema — all 8 existing tables from gaokao B2C MVP

Revision ID: 001
Revises: None
Create Date: 2026-05-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("region", sa.String(50), server_default=""),
        sa.Column("score", sa.Integer, server_default="0"),
        sa.Column("subjects", sa.String(100), server_default=""),
        sa.Column("batch", sa.String(20), server_default="本科批"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "colleges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), unique=True),
        sa.Column("type", sa.String(20)),
        sa.Column("level", sa.String(50)),
        sa.Column("province", sa.String(50)),
        sa.Column("city", sa.String(50)),
        sa.Column("is_985", sa.Boolean, server_default="false"),
        sa.Column("is_211", sa.Boolean, server_default="false"),
        sa.Column("is_double_first", sa.Boolean, server_default="false"),
        sa.Column("intro", sa.Text, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "admission_data",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("college_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("major_name", sa.String(100), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("province", sa.String(50), server_default="广东"),
        sa.Column("batch", sa.String(50)),
        sa.Column("min_score", sa.Integer),
        sa.Column("min_rank", sa.Integer, nullable=True),
        sa.Column("subject_requirements", sa.String(200)),
        sa.Column("source_url", sa.String(500), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "user_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("profile_json", JSONB, server_default="{}"),
        sa.Column("confidence_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("profile_version", sa.Integer, server_default="1"),
        sa.Column("result_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "recommendation_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("college_name", sa.String(200)),
        sa.Column("major_name", sa.String(200)),
        sa.Column("feedback_type", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "industry_analysis",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("industry_name", sa.String(100), nullable=False, index=True),
        sa.Column("industry_code", sa.String(20), server_default=""),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("avg_annual_salary", sa.Float, nullable=True),
        sa.Column("salary_growth_rate", sa.Float, nullable=True),
        sa.Column("employment_demand_index", sa.Float, nullable=True),
        sa.Column("industry_growth_rate", sa.Float, nullable=True),
        sa.Column("entry_difficulty", sa.String(20), server_default="中等"),
        sa.Column("popular_positions", JSONB, server_default="[]"),
        sa.Column("career_path", sa.String(500), server_default=""),
        sa.Column("pros", JSONB, server_default="[]"),
        sa.Column("cons", JSONB, server_default="[]"),
        sa.Column("insider_reviews", JSONB, server_default="[]"),
        sa.Column("related_majors", JSONB, server_default="[]"),
        sa.Column("outlook", sa.String(1000), server_default=""),
        sa.Column("source", sa.String(500), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "major_industry_mapping",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("major_name", sa.String(100), nullable=False, index=True),
        sa.Column("primary_industries", JSONB, server_default="[]"),
        sa.Column("secondary_industries", JSONB, server_default="[]"),
        sa.Column("typical_positions", JSONB, server_default="[]"),
        sa.Column("salary_range", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("major_industry_mapping")
    op.drop_table("industry_analysis")
    op.drop_table("recommendation_feedback")
    op.drop_table("recommendations")
    op.drop_table("user_profiles")
    op.drop_table("admission_data")
    op.drop_table("colleges")
    op.drop_table("users")
