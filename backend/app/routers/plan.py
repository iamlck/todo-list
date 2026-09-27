"""Reading, setting up and editing a user's plan."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession, get_owned_day, get_owned_task
from app.models import Day, DeletedTask, Task, UserSettings
from app.schemas import (
    CarryForwardIn,
    DeletedTaskOut,
    DeleteResultOut,
    CarryForwardOut,
    DayCreate,
    DayOut,
    DayRestoreIn,
    DayUpdate,
    DeleteImpactOut,
    MoveTasksIn,
    PlanOut,
    ReorderIn,
    SettingsIn,
    SettingsOut,
    SetupIn,
    TaskCreate,
    TaskOut,
    TaskReorderIn,
    TaskReorderIn as _TaskReorderIn,  # noqa: F401  (kept for clarity in imports)
    TaskRestoreIn,
    TaskUpdate,
)
from app.services import plan as plan_service

router = APIRouter(prefix="/me", tags=["plan"])


def _serialize_task(task: Task, progress: dict) -> TaskOut:
    row = progress.get(task.id)
    return TaskOut(
        id=task.id,
        title=task.title,
        position=task.position,
        completed=plan_service.is_completed(task, progress),
        status=plan_service.task_status(task, progress),
        started_at=row.started_at if row else None,
        notes=row.notes if row else "",
        # A main task shows its own time plus everything beneath it.
        minutes_spent=plan_service.minutes_for(task, progress),
        timer_started_at=row.timer_started_at if row else None,
        carried_count=task.carried_count,
        original_day_position=task.original_day_position,
        last_carried_from=task.last_carried_from,
        subtasks=[
            _serialize_task(sub, progress)
            for sub in sorted(task.subtasks, key=lambda t: t.position)
        ],
    )


def _serialize_day(day: Day, progress: dict) -> DayOut:
    return DayOut(
        id=day.id,
        position=day.position,
        title=day.title,
        tasks=[
            _serialize_task(t, progress)
            for t in sorted(
                (t for t in day.tasks if t.parent_id is None), key=lambda t: t.position
            )
        ],
    )


@router.get("/plan", response_model=PlanOut)
def get_plan(user: CurrentUser, db: DbSession) -> PlanOut:
    days = plan_service.load_plan(db, user)
    progress = plan_service.progress_by_task(db, user)
    settings = user.settings
    return PlanOut(
        start_date=settings.start_date if settings else None,
        onboarded=bool(settings and settings.onboarded),
        days=[_serialize_day(d, progress) for d in days],
    )


# --- setting up ---------------------------------------------------------


@router.post("/plan/setup", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def setup_plan(body: SetupIn, user: CurrentUser, db: DbSession) -> PlanOut:
    """Create the plan for an account that does not have one yet.

    Refused once a plan exists, so an accidental second call cannot wipe out
    work. Start again by deleting the days first.
    """
    existing = db.scalar(select(Day).where(Day.user_id == user.id).limit(1))
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="You already have a plan. Edit it, or delete its days to start over.",
        )

    if body.mode == "default":
        plan_service.clone_default_plan(db, user)
    elif body.mode == "blank":
        if not body.day_count:
            raise HTTPException(status_code=400, detail="Say how many days the plan should have")
        plan_service.blank_plan(db, user, body.day_count)
    else:  # import
        if not body.days:
            raise HTTPException(status_code=400, detail="The uploaded file had no rows")
        plan_service.build_plan(
            db,
            user,
            [
                {
                    "title": d.title,
                    "tasks": [{"title": t.title, "subtasks": t.subtasks} for t in d.tasks],
                }
                for d in body.days
            ],
        )

    settings = user.settings or UserSettings(user_id=user.id)
    settings.onboarded = True
    db.add(settings)
    db.commit()

    days = plan_service.load_plan(db, user)
    progress = plan_service.progress_by_task(db, user)
    return PlanOut(
        start_date=settings.start_date,
        onboarded=True,
        days=[_serialize_day(d, progress) for d in days],
    )


# --- days ---------------------------------------------------------------


@router.post("/days", response_model=DayOut, status_code=status.HTTP_201_CREATED)
def create_day(body: DayCreate, user: CurrentUser, db: DbSession) -> DayOut:
    day = plan_service.insert_day(db, user, body.title, body.position)
    db.commit()
    db.refresh(day)
    return _serialize_day(day, {})


@router.patch("/days/{day_id}", response_model=DayOut)
def rename_day(day_id: uuid.UUID, body: DayUpdate, user: CurrentUser, db: DbSession) -> DayOut:
    day = get_owned_day(db, user, day_id)
    day.title = body.title
    db.commit()
    db.refresh(day)
    return _serialize_day(day, plan_service.progress_by_task(db, user))


@router.get("/days/{day_id}/delete-impact", response_model=DeleteImpactOut)
def day_delete_impact(day_id: uuid.UUID, user: CurrentUser, db: DbSession) -> DeleteImpactOut:
    """Lets the UI warn about lost work before the user confirms."""
    day = get_owned_day(db, user, day_id)
    tasks, completed, minutes = plan_service.delete_impact(db, day)
    return DeleteImpactOut(tasks=tasks, completed_tasks=completed, minutes_spent=minutes)


@router.delete("/days/{day_id}", response_model=DeleteResultOut)
def delete_day(day_id: uuid.UUID, user: CurrentUser, db: DbSession) -> DeleteResultOut:
    day = get_owned_day(db, user, day_id)

    entries = plan_service.log_day_deletion(db, user, day)
    db.flush()
    log_ids = [e.id for e in entries]

    db.delete(day)  # cascades to its tasks and their progress
    db.flush()
    plan_service.compact_day_positions(db, user)
    db.commit()
    return DeleteResultOut(deleted_log_ids=log_ids)


@router.put("/days/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_days(body: ReorderIn, user: CurrentUser, db: DbSession) -> Response:
    days = {d.id: d for d in plan_service.load_plan(db, user)}
    if set(body.ids) != set(days):
        raise HTTPException(status_code=400, detail="Send every day id exactly once")
    plan_service.apply_order(days, body.ids)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- carry forward ------------------------------------------------------


@router.post("/days/{day_id}/carry-forward", response_model=CarryForwardOut)
def carry_forward(
    day_id: uuid.UUID, body: CarryForwardIn, user: CurrentUser, db: DbSession
) -> CarryForwardOut:
    """Move chosen unfinished tasks from this day to another day."""
    day = get_owned_day(db, user, day_id)
    progress = plan_service.progress_by_task(db, user)

    if body.task_ids is None:
        # Everything unfinished: whole main tasks where possible, otherwise
        # the individual unfinished subtasks.
        selected: list[uuid.UUID] = []
        for task in (t for t in day.tasks if t.parent_id is None):
            if plan_service.is_completed(task, progress):
                continue
            if task.subtasks and any(plan_service.is_completed(s, progress) for s in task.subtasks):
                selected.extend(
                    s.id for s in task.subtasks if not plan_service.is_completed(s, progress)
                )
            else:
                selected.append(task.id)
    else:
        if not body.task_ids:
            raise HTTPException(status_code=400, detail="Choose at least one task to move")
        on_this_day = {t.id for t in day.tasks}
        unknown = [str(i) for i in body.task_ids if i not in on_this_day]
        if unknown:
            raise HTTPException(
                status_code=400, detail="Those tasks are not on this day: " + ", ".join(unknown)
            )
        selected = body.task_ids

    if body.target_day_id is not None:
        target = get_owned_day(db, user, body.target_day_id)
        if target.id == day.id:
            raise HTTPException(status_code=400, detail="Pick a different day to move them to")
    else:
        target = db.scalar(
            select(Day)
            .where(Day.user_id == user.id, Day.position > day.position)
            .order_by(Day.position)
            .limit(1)
        )
        if target is None:
            raise HTTPException(
                status_code=400,
                detail="This is the last day. Add a day first, or choose an earlier one.",
            )

    moved_ids = plan_service.carry_forward(db, user, day, target, selected)
    db.commit()
    return CarryForwardOut(
        moved=len(moved_ids), target_day_position=target.position, moved_task_ids=moved_ids
    )


# --- tasks --------------------------------------------------------------


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, user: CurrentUser, db: DbSession) -> TaskOut:
    day = get_owned_day(db, user, body.day_id)
    parent = None
    if body.parent_id is not None:
        parent = get_owned_task(db, user, body.parent_id)
        if parent.parent_id is not None:
            # Two levels is the whole model; deeper nesting would complicate
            # progress counting for no real gain.
            raise HTTPException(status_code=400, detail="Subtasks cannot have subtasks")
        if parent.day_id != day.id:
            raise HTTPException(status_code=400, detail="That task is on a different day")

    task = plan_service.insert_task(db, day, parent, body.title)
    db.commit()
    db.refresh(task)
    return _serialize_task(task, {})


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def rename_task(
    task_id: uuid.UUID, body: TaskUpdate, user: CurrentUser, db: DbSession
) -> TaskOut:
    task = get_owned_task(db, user, task_id)
    # Renaming never touches progress: it is keyed by task id.
    task.title = body.title
    db.commit()
    db.refresh(task)
    return _serialize_task(task, plan_service.progress_by_task(db, user))


@router.delete("/tasks/{task_id}", response_model=DeleteResultOut)
def delete_task(task_id: uuid.UUID, user: CurrentUser, db: DbSession) -> DeleteResultOut:
    task = get_owned_task(db, user, task_id)
    day, parent_id = task.day, task.parent_id

    # Logged before the row goes, while its details can still be read.
    entry = plan_service.log_deletion(
        db, user, task, plan_service.progress_by_task(db, user), reason="task"
    )
    db.flush()
    log_id = entry.id

    db.delete(task)  # cascades to its subtasks
    db.flush()
    db.refresh(day)
    plan_service.compact_task_positions(db, day, parent_id)
    db.commit()
    return DeleteResultOut(deleted_log_ids=[log_id])


@router.put("/tasks/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_tasks(body: TaskReorderIn, user: CurrentUser, db: DbSession) -> Response:
    day = get_owned_day(db, user, body.day_id)
    tasks = {t.id: t for t in day.tasks if t.parent_id == body.parent_id}
    if set(body.ids) != set(tasks):
        raise HTTPException(
            status_code=400, detail="Send every task id at this level exactly once"
        )
    plan_service.apply_order(tasks, body.ids)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- history ------------------------------------------------------------


def _mark_restored(db, user, log_ids: list[uuid.UUID]) -> None:
    """Stop history entries claiming a task is gone once it has come back."""
    if not log_ids:
        return
    entries = db.scalars(
        select(DeletedTask).where(
            DeletedTask.id.in_(log_ids),
            DeletedTask.user_id == user.id,
            DeletedTask.restored_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    for entry in entries:
        entry.restored_at = now


@router.get("/deleted-tasks", response_model=list[DeletedTaskOut])
def deleted_tasks(
    user: CurrentUser, db: DbSession, limit: int = 100, include_restored: bool = True
) -> list[DeletedTaskOut]:
    """The history of deleted tasks, newest first.

    A log, not a recycle bin: it records what went and when, and holds nothing
    that can be put back.
    """
    stmt = select(DeletedTask).where(DeletedTask.user_id == user.id)
    if not include_restored:
        stmt = stmt.where(DeletedTask.restored_at.is_(None))
    rows = db.scalars(stmt.order_by(DeletedTask.deleted_at.desc()).limit(min(limit, 500)))
    return [DeletedTaskOut.model_validate(r) for r in rows]


# --- undo ---------------------------------------------------------------


@router.post("/tasks/move", status_code=status.HTTP_204_NO_CONTENT)
def move_tasks(body: MoveTasksIn, user: CurrentUser, db: DbSession) -> Response:
    """Move specific tasks to a day. This is how a carry-forward is undone."""
    target = get_owned_day(db, user, body.target_day_id)
    tasks = [get_owned_task(db, user, task_id) for task_id in body.task_ids]
    plan_service.move_tasks(db, tasks, target)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/tasks/restore", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def restore_task(body: TaskRestoreIn, user: CurrentUser, db: DbSession) -> TaskOut:
    """Recreate a deleted task with its progress and subtasks.

    The task gets a new id — the original row is gone — but everything
    recorded against it comes back.
    """
    day = get_owned_day(db, user, body.day_id)
    parent = get_owned_task(db, user, body.parent_id) if body.parent_id else None

    task = plan_service.insert_task(
        db, day, parent, body.title, body.position, body.completed, body.notes, body.minutes_spent
    )
    for child in body.subtasks:
        plan_service.insert_task(
            db, day, task, child.title, child.position, child.completed,
            child.notes, child.minutes_spent,
        )
    _mark_restored(db, user, body.deleted_log_ids)
    db.commit()
    db.refresh(task)
    return _serialize_task(task, plan_service.progress_by_task(db, user))


@router.post("/days/restore", response_model=DayOut, status_code=status.HTTP_201_CREATED)
def restore_day(body: DayRestoreIn, user: CurrentUser, db: DbSession) -> DayOut:
    """Recreate a deleted day and everything that was on it."""
    day = plan_service.insert_day(db, user, body.title, body.position)
    for spec in body.tasks:
        task = plan_service.insert_task(
            db, day, None, spec.title, spec.position, spec.completed,
            spec.notes, spec.minutes_spent,
        )
        for child in spec.subtasks:
            plan_service.insert_task(
                db, day, task, child.title, child.position, child.completed,
                child.notes, child.minutes_spent,
            )
    _mark_restored(db, user, body.deleted_log_ids)
    db.commit()
    db.refresh(day)
    return _serialize_day(day, plan_service.progress_by_task(db, user))


# --- settings -----------------------------------------------------------


@router.put("/settings", response_model=SettingsOut)
def update_settings(body: SettingsIn, user: CurrentUser, db: DbSession) -> SettingsOut:
    """Changing the start date only moves "today"; progress is untouched."""
    row = user.settings or UserSettings(user_id=user.id)
    row.start_date = body.start_date
    db.add(row)
    db.commit()
    return SettingsOut(start_date=row.start_date)
