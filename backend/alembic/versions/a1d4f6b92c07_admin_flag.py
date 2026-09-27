"""admin flag on users

Revision ID: a1d4f6b92c07
Revises: 9c3b7e21a840
"""
import sqlalchemy as sa
from alembic import op

revision = "a1d4f6b92c07"
down_revision = "9c3b7e21a840"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false")
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
