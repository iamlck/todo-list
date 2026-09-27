"""Completion, notes and time spent."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser, DbSession, get_owned_task
from app.schemas import NotesIn, ProgressIn, ProgressOut, StartIn, TimeIn
from app.services import plan as plan_service

router = APIRouter(prefix="/me/progress", tags=["progress"])


def _status(row) -> str:
    if row.completed:
        return "completed"
    return "in-progress" if row.started_at is not None else "not-started"


def _out(task_id: uuid.UUID, row) -> ProgressOut:
    return ProgressOut(
        task_id=task_id,
        completed=row.completed,
        status=_status(row),
        started_at=row.started_at,
        notes=row.notes,
        minutes_spent=row.minutes_spent,
        timer_started_at=row.timer_started_at,
    )


@router.put("/{task_id}", response_model=ProgressOut)
def set_completed(
    task_id: uuid.UUID, body: ProgressIn, user: CurrentUser, db: DbSession
) -> ProgressOut:
    """Tick or untick a task.

    Ticking a main task ticks all of its subtasks, because a main task is a
    container: it is complete exactly when its children are.
    """
    task = get_owned_task(db, user, task_id)

    now = datetime.now(timezone.utc)
    row = plan_service.get_or_create_progress(db, user, task)
    row.completed = body.completed
    if body.completed:
        # Finishing work should not leave a timer running against it, and
        # something finished was self-evidently started.
        plan_service.stop_timer(row)
        if row.started_at is None:
            row.started_at = now

    for sub in task.subtasks:
        child = plan_service.get_or_create_progress(db, user, sub)
        child.completed = body.completed
        if body.completed:
            plan_service.stop_timer(child)
            if child.started_at is None:
                child.started_at = now

    db.commit()
    return _out(task.id, row)


@router.put("/{task_id}/notes", response_model=ProgressOut)
def set_notes(task_id: uuid.UUID, body: NotesIn, user: CurrentUser, db: DbSession) -> ProgressOut:
    """Save notes against a task. A task can carry notes while unticked."""
    task = get_owned_task(db, user, task_id)
    row = plan_service.get_or_create_progress(db, user, task)
    row.notes = body.notes
    db.commit()
    return _out(task.id, row)


@router.put("/{task_id}/time", response_model=ProgressOut)
def set_time(task_id: uuid.UUID, body: TimeIn, user: CurrentUser, db: DbSession) -> ProgressOut:
    """Record time by hand: set the total, or adjust it by `add_minutes`."""
    if body.minutes_spent is None and body.add_minutes is None:
        raise HTTPException(status_code=400, detail="Send minutes_spent or add_minutes")

    task = get_owned_task(db, user, task_id)
    row = plan_service.get_or_create_progress(db, user, task)

    if body.minutes_spent is not None:
        row.minutes_spent = body.minutes_spent
    if body.add_minutes:
        # Never let an adjustment push the total below zero.
        row.minutes_spent = max(0, row.minutes_spent + body.add_minutes)

    db.commit()
    return _out(task.id, row)


@router.post("/{task_id}/timer/start", response_model=ProgressOut)
def start_timer(task_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ProgressOut:
    """Start timing this task, stopping any timer already running elsewhere.

    Only one timer runs at a time: two at once would double-count the same
    stretch of work.
    """
    task = get_owned_task(db, user, task_id)

    for other in plan_service.progress_by_task(db, user).values():
        if other.timer_started_at is not None and other.task_id != task.id:
            plan_service.stop_timer(other)

    row = plan_service.get_or_create_progress(db, user, task)
    now = datetime.now(timezone.utc)
    if row.timer_started_at is None:
        row.timer_started_at = now
    # Timing something implies it is underway.
    if row.started_at is None:
        row.started_at = now
    db.commit()
    return _out(task.id, row)


@router.post("/{task_id}/timer/stop", response_model=ProgressOut)
def stop_timer(task_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ProgressOut:
    """Stop the timer and fold the elapsed minutes into the total."""
    task = get_owned_task(db, user, task_id)
    row = plan_service.get_or_create_progress(db, user, task)
    plan_service.stop_timer(row)
    db.commit()
    return _out(task.id, row)


@router.put("/{task_id}/start", response_model=ProgressOut)
def set_started(
    task_id: uuid.UUID, body: StartIn, user: CurrentUser, db: DbSession
) -> ProgressOut:
    """Mark a task in progress, or clear it back to not started.

    Separate from the timer: you can flag something as underway without
    timing it. Starting a timer also marks the task started, so a running
    timer never sits against a task labelled "not started".
    """
    task = get_owned_task(db, user, task_id)
    row = plan_service.get_or_create_progress(db, user, task)

    if body.started:
        if row.started_at is None:
            row.started_at = datetime.now(timezone.utc)
    else:
        row.started_at = None
        row.completed = False
        plan_service.stop_timer(row)

    db.commit()
    return _out(task.id, row)
