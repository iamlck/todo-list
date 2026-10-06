"""Request and response shapes. FastAPI validates every payload against these."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- auth ---------------------------------------------------------------


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    is_admin: bool = False


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountIn(BaseModel):
    """Deleting an account is permanent, so it asks for the password again."""

    password: str
    # The user must type their own email to confirm, the way GitHub and
    # similar tools guard irreversible deletions.
    confirm_email: EmailStr


class AccountSummaryOut(BaseModel):
    """What deleting the account would destroy, shown before confirming."""

    email: str
    days: int
    tasks: int
    completed_tasks: int
    notes: int
    minutes_spent: int


# --- the plan -----------------------------------------------------------


class TaskOut(BaseModel):
    id: uuid.UUID
    title: str
    position: int
    completed: bool
    # "not-started" | "in-progress" | "completed"
    status: str = "not-started"
    started_at: datetime | None = None
    notes: str = ""
    minutes_spent: int = 0
    timer_started_at: datetime | None = None
    # Carry-forward history, so the UI can show "carried forward twice".
    carried_count: int = 0
    original_day_position: int | None = None
    last_carried_from: int | None = None
    subtasks: list["TaskOut"] = []


class DayOut(BaseModel):
    id: uuid.UUID
    position: int
    title: str
    tasks: list[TaskOut]


class PlanOut(BaseModel):
    start_date: date | None
    onboarded: bool
    days: list[DayOut]


# --- setting up a plan --------------------------------------------------


class ImportSubtask(BaseModel):
    title: str = Field(min_length=1, max_length=500)


class ImportTask(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    subtasks: list[str] = []


class ImportDay(BaseModel):
    title: str = Field(default="", max_length=200)
    tasks: list[ImportTask] = []


class SetupIn(BaseModel):
    """How to create the plan for a new account.

    - `default` copies the built-in 20-day CloudOps / Kubernetes / GenAI plan
    - `blank` creates `day_count` empty days to fill in by hand
    - `import` builds the plan from uploaded rows
    """

    mode: str = Field(pattern="^(default|blank|import)$")
    day_count: int | None = Field(default=None, ge=1, le=365)
    days: list[ImportDay] | None = None


# --- editing ------------------------------------------------------------


class DayCreate(BaseModel):
    title: str = Field(default="", max_length=200)
    position: int | None = Field(default=None, ge=1)


class DayUpdate(BaseModel):
    title: str = Field(max_length=200)


class TaskCreate(BaseModel):
    day_id: uuid.UUID
    # Omit for a main task; set it to add a subtask under that task.
    parent_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=500)


class TaskUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=500)


class ReorderIn(BaseModel):
    """The complete ordered list of ids; positions are rewritten to match."""

    ids: list[uuid.UUID]


class TaskReorderIn(ReorderIn):
    day_id: uuid.UUID
    parent_id: uuid.UUID | None = None


class StartIn(BaseModel):
    """Mark a task started, or clear that back to not started."""

    started: bool = True


class DeletedTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    day_position: int | None
    day_title: str
    parent_title: str | None
    was_completed: bool
    minutes_spent: int
    subtask_count: int
    reason: str
    deleted_at: datetime
    restored_at: datetime | None


class DeleteResultOut(BaseModel):
    """The log entry a delete created, so an undo can mark it restored."""

    deleted_log_ids: list[uuid.UUID] = []


class DeleteImpactOut(BaseModel):
    """What a delete would destroy, so the UI can warn before confirming."""

    tasks: int
    completed_tasks: int
    minutes_spent: int


# --- progress, time, settings -------------------------------------------


class ProgressIn(BaseModel):
    completed: bool


class NotesIn(BaseModel):
    notes: str = Field(default="", max_length=5000)


class TimeIn(BaseModel):
    """Set the recorded time outright, or add to it with `add_minutes`."""

    minutes_spent: int | None = Field(default=None, ge=0, le=60 * 24 * 365)
    add_minutes: int | None = Field(default=None, ge=-10000, le=10000)


class ProgressOut(BaseModel):
    task_id: uuid.UUID
    completed: bool
    status: str = "not-started"
    started_at: datetime | None = None
    notes: str = ""
    minutes_spent: int = 0
    timer_started_at: datetime | None = None


class SettingsIn(BaseModel):
    start_date: date | None = None


class SettingsOut(BaseModel):
    start_date: date | None


# --- carry forward and undo ---------------------------------------------


class CarryForwardIn(BaseModel):
    """Which tasks to carry forward, and where.

    `task_ids` selects them; omitting it carries everything unfinished.
    `target_day_id` defaults to the next day, or the previous one when
    `direction` is "previous".
    """

    task_ids: list[uuid.UUID] | None = None
    target_day_id: uuid.UUID | None = None
    direction: Literal["next", "previous"] = "next"


class CarryForwardOut(BaseModel):
    moved: int
    target_day_position: int
    moved_task_ids: list[uuid.UUID] = []


class MoveTasksIn(BaseModel):
    """Move specific tasks to a day. Used to undo a carry-forward."""

    task_ids: list[uuid.UUID]
    target_day_id: uuid.UUID


class TaskRestoreIn(BaseModel):
    """Recreate a deleted task, including its progress and subtasks."""

    # When given, the matching history entries are marked restored rather
    # than left claiming the task is gone.
    deleted_log_ids: list[uuid.UUID] = []
    day_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    position: int | None = Field(default=None, ge=1)
    completed: bool = False
    notes: str = Field(default="", max_length=5000)
    minutes_spent: int = 0
    subtasks: list["TaskRestoreChild"] = []


class TaskRestoreChild(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    position: int | None = Field(default=None, ge=1)
    completed: bool = False
    notes: str = Field(default="", max_length=5000)
    minutes_spent: int = 0


class DayRestoreIn(BaseModel):
    """Recreate a deleted day and everything that was on it."""

    deleted_log_ids: list[uuid.UUID] = []
    title: str = Field(default="", max_length=200)
    position: int | None = Field(default=None, ge=1)
    tasks: list[TaskRestoreIn] = []


# --- administration -----------------------------------------------------


class AdminUserOut(BaseModel):
    """A user as the admin list shows them.

    Counts and totals only: an administrator can see how much work an account
    holds, not read the notes inside it.
    """

    id: uuid.UUID
    email: str
    is_admin: bool
    created_at: datetime
    onboarded: bool
    start_date: date | None
    days: int
    tasks: int
    completed_tasks: int
    minutes_spent: int
    last_activity: datetime | None


class AdminUserUpdate(BaseModel):
    is_admin: bool


class AdminDeleteIn(BaseModel):
    """Deleting someone else's account asks for your own password."""

    password: str
    confirm_email: EmailStr
