"""tasks and subtasks, time tracking, carry-forward history

Replaces the fixed CloudOps/Kubernetes/GenAI `track` column with a
self-referencing `tasks` table: each track becomes a main task and its topics
become subtasks. Existing plans and progress are migrated, not discarded.

Revision ID: 8f2a1c4d5e60
Revises: 754218db8611
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "8f2a1c4d5e60"
down_revision = "754218db8611"
branch_labels = None
depends_on = None

TRACK_LABELS = {"cloudops": "AWS CloudOps", "kubernetes": "Kubernetes", "genai": "GenAI"}
TRACK_ORDER = ["cloudops", "kubernetes", "genai"]


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("onboarded", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "day_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("days.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("carried_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("original_day_position", sa.Integer(), nullable=True),
        sa.Column("last_carried_from", sa.Integer(), nullable=True),
        sa.Column("last_carried_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tasks_day_id", "tasks", ["day_id"])
    op.create_index("ix_tasks_parent_id", "tasks", ["parent_id"])

    op.create_table(
        "task_progress",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("minutes_spent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("timer_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_task_progress_user_id", "task_progress", ["user_id"])

    _migrate_topics_to_tasks()

    op.drop_table("topic_progress")
    op.drop_table("topics")
    sa.Enum(name="track").drop(op.get_bind(), checkfirst=True)

    # Anyone who already has a plan has, in effect, finished onboarding.
    op.execute(
        "UPDATE user_settings SET onboarded = true "
        "WHERE user_id IN (SELECT DISTINCT user_id FROM days)"
    )


def _migrate_topics_to_tasks() -> None:
    """Turn each day's tracks into main tasks and its topics into subtasks."""
    conn = op.get_bind()

    days = conn.execute(
        sa.text("SELECT id, user_id, position FROM days ORDER BY user_id, position")
    ).fetchall()

    for day_id, user_id, _position in days:
        topics = conn.execute(
            sa.text(
                "SELECT t.id, t.track, t.title, t.position, "
                "       COALESCE(p.completed, false), COALESCE(p.notes, '') "
                "FROM topics t "
                "LEFT JOIN topic_progress p ON p.topic_id = t.id "
                "WHERE t.day_id = :day_id "
                "ORDER BY t.position"
            ),
            {"day_id": day_id},
        ).fetchall()
        if not topics:
            continue

        by_track: dict[str, list] = {}
        for row in topics:
            by_track.setdefault(str(row[1]), []).append(row)

        # Preserve the original CloudOps / Kubernetes / GenAI ordering, then
        # anything unexpected, so a migrated plan reads as it did before.
        ordered = [k for k in TRACK_ORDER if k in by_track]
        ordered += [k for k in by_track if k not in TRACK_ORDER]

        for main_position, track in enumerate(ordered, start=1):
            main_id = conn.execute(
                sa.text(
                    "INSERT INTO tasks (id, day_id, parent_id, title, position, carried_count) "
                    "VALUES (gen_random_uuid(), :day_id, NULL, :title, :position, 0) "
                    "RETURNING id"
                ),
                {
                    "day_id": day_id,
                    "title": TRACK_LABELS.get(track, track),
                    "position": main_position,
                },
            ).scalar()

            for sub_position, row in enumerate(by_track[track], start=1):
                _topic_id, _track, title, _pos, completed, notes = row
                sub_id = conn.execute(
                    sa.text(
                        "INSERT INTO tasks "
                        "(id, day_id, parent_id, title, position, carried_count) "
                        "VALUES (gen_random_uuid(), :day_id, :parent_id, :title, :position, 0) "
                        "RETURNING id"
                    ),
                    {
                        "day_id": day_id,
                        "parent_id": main_id,
                        "title": title,
                        "position": sub_position,
                    },
                ).scalar()

                if completed or notes:
                    conn.execute(
                        sa.text(
                            "INSERT INTO task_progress "
                            "(task_id, user_id, completed, notes, minutes_spent) "
                            "VALUES (:task_id, :user_id, :completed, :notes, 0)"
                        ),
                        {
                            "task_id": sub_id,
                            "user_id": user_id,
                            "completed": completed,
                            "notes": notes,
                        },
                    )


def downgrade() -> None:
    # One-way: the track enum cannot be reconstructed from free-text task
    # titles without guessing. Restore from a backup instead.
    raise NotImplementedError(
        "Downgrade is not supported. Restore from a pg_dump backup taken before the upgrade."
    )
