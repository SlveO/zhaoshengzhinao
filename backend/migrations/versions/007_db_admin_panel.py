"""db admin panel: add users.rank

Revision ID: 007_db_admin_panel
Revises: 006
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa


revision = "007_db_admin_panel"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("rank", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "rank")
