"""add session TTL

Revision ID: 006
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"


def upgrade():
    op.add_column("consult_sessions", sa.Column(
        "expires_at", sa.DateTime(timezone=True), nullable=True,
        comment="Session expiry: 1 day for guests, 30 days for registered, null = never expires"
    ))
    op.execute("""
        UPDATE consult_sessions
        SET expires_at = created_at + INTERVAL '1 day'
        WHERE user_id IS NULL AND expires_at IS NULL
    """)


def downgrade():
    op.drop_column("consult_sessions", "expires_at")
