"""Database tables.

Layout notes:
  - Days and tasks belong to a user, so every learner owns an editable plan.
  - A day's number is derived from `position`; it is never stored twice.
  - `tasks` is self-referencing: a row with `parent_id` set is a subtask.
  - Completion, notes and time live in their own table keyed by task id, so
    renaming, reordering or carrying a task forward never disturbs progress.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Granted from the command line (scripts/make_admin.py); there is
    # deliberately no way to promote yourself through the UI.
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    settings: Mapped["UserSettings"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    days: Mapped[list["Day"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="Day.position"
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Null until the learner picks one; "current day" is computed from it.
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # False until a plan has been chosen, which is what sends a new account to
    # the setup screen instead of an empty dashboard.
    onboarded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    user: Mapped[User] = relationship(back_populates="settings")


class Day(Base):
    __tablename__ = "days"
    # Deferrable: a reorder rewrites several positions in one transaction and
    # would otherwise collide part-way through. Postgres checks this at COMMIT.
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "position",
            name="uq_days_user_position",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    user: Mapped[User] = relationship(back_populates="days")
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="day", cascade="all, delete-orphan", order_by="Task.position"
    )


class Task(Base):
    """A main task or a subtask.

    One self-referencing table holds both: a row with `parent_id` set is a
    subtask of that row. Keeping them in one table means completion, notes,
    time and carry-forward are implemented once rather than twice.
    """

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = _uuid_pk()
    day_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    # Ordering among siblings: within the day for main tasks, within the
    # parent for subtasks.
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- carry-forward history -----------------------------------------
    # Held on the task so the history survives whether or not progress exists.
    carried_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    original_day_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_carried_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_carried_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    day: Mapped[Day] = relationship(back_populates="tasks")
    parent: Mapped["Task | None"] = relationship(
        back_populates="subtasks", remote_side=[id]
    )
    subtasks: Mapped[list["Task"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan", order_by="Task.position"
    )
    progress: Mapped["TaskProgress"] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False
    )


class TaskProgress(Base):
    """Per-task state: completion, notes, and time spent."""

    __tablename__ = "task_progress"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    # Denormalised from task -> day -> user so a user's progress can be
    # counted without joining through the tree.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Set when the learner presses Start. Together with `completed` this gives
    # the three states: not started, in progress, completed.
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")

    # Total recorded effort. Manual entries and finished timer runs both add
    # into this single figure.
    minutes_spent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Set while a timer is running, null otherwise. Elapsed time is folded
    # into minutes_spent when the timer stops.
    timer_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    task: Mapped[Task] = relationship(back_populates="progress")


class PasswordResetToken(Base):
    """A single-use, expiring token for resetting a forgotten password.

    Only a hash of the token is stored, so a leaked database still does not
    hand over working reset links.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DeletedTask(Base):
    """A record of a task that was deleted.

    A history log, not a recycle bin: it answers "what happened to that task?"
    and keeps no rows to restore from. Undo within a session still works, and
    marks the entry restored rather than leaving a misleading record.
    """

    __tablename__ = "deleted_tasks"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    # Where it was, captured at deletion time: the day itself may be gone.
    day_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    parent_title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # What was lost with it.
    was_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    minutes_spent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subtask_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # "day" when the whole day was removed, "task" for a single task.
    reason: Mapped[str] = mapped_column(String(20), nullable=False, default="task")

    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
