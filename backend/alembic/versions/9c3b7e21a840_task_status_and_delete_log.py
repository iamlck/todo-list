"""explicit start state, and a log of deleted tasks

Revision ID: 9c3b7e21a840
Revises: 8f2a1c4d5e60
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "9c3b7e21a840"
down_revision = "8f2a1c4d5e60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task_progress", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True)
    )
    # Anything already finished was self-evidently started; backfilling keeps
    # existing plans from showing completed work as "not started".
    op.execute("UPDATE task_progress SET started_at = updated_at WHERE completed = true")

    op.create_table(
        "deleted_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("day_position", sa.Integer(), nullable=True),
        sa.Column("day_title", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("parent_title", sa.String(length=500), nullable=True),
        sa.Column("was_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("minutes_spent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subtask_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(length=20), nullable=False, server_default="task"),
        sa.Column(
            "deleted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_deleted_tasks_user_id", "deleted_tasks", ["user_id"])


def downgrade() -> None:
    op.drop_table("deleted_tasks")
    op.drop_column("task_progress", "started_at")
