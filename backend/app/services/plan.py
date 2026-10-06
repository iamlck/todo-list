"""Plan logic, kept out of the HTTP layer so it can be tested directly.

A plan is days -> main tasks -> subtasks. Only *leaf* tasks count towards
progress: a main task with subtasks is a container, and counting both it and
its children would double-count the same work.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.data.default_plan import DEFAULT_PLAN
from app.models import Day, DeletedTask, Task, TaskProgress, User


# --- building plans -----------------------------------------------------


def build_plan(db: Session, user: User, days_spec: list[dict]) -> None:
    """Create days, main tasks and subtasks from a plain spec.

    The spec shape — `[{title, tasks: [{title, subtasks: [str]}]}]` — is shared
    by the default plan, a CSV upload and a generated blank plan, so all three
    routes through setup end in the same place.
    """
    for day_index, day_spec in enumerate(days_spec, start=1):
        day = Day(user_id=user.id, position=day_index, title=day_spec.get("title", ""))
        db.add(day)
        db.flush()

        for task_index, task_spec in enumerate(day_spec.get("tasks", []), start=1):
            task = Task(
                day_id=day.id,
                parent_id=None,
                title=task_spec["title"],
                position=task_index,
                original_day_position=day_index,
            )
            db.add(task)
            db.flush()

            for sub_index, sub_title in enumerate(task_spec.get("subtasks", []), start=1):
                db.add(
                    Task(
                        day_id=day.id,
                        parent_id=task.id,
                        title=sub_title,
                        position=sub_index,
                        original_day_position=day_index,
                    )
                )


def clone_default_plan(db: Session, user: User) -> None:
    """Give a user their own editable copy of the default plan."""
    build_plan(db, user, DEFAULT_PLAN)


def blank_plan(db: Session, user: User, day_count: int) -> None:
    """Create `day_count` empty days, to be filled in from the editor."""
    build_plan(db, user, [{"title": "", "tasks": []} for _ in range(day_count)])


# --- reading ------------------------------------------------------------


def load_plan(db: Session, user: User) -> list[Day]:
    """All of a user's days with their task tree, ordered by position."""
    return list(
        db.scalars(
            select(Day)
            .where(Day.user_id == user.id)
            .order_by(Day.position)
            .options(selectinload(Day.tasks).selectinload(Task.subtasks))
        )
    )


def progress_by_task(db: Session, user: User) -> dict[uuid.UUID, TaskProgress]:
    """Map task id -> its progress row. A missing entry means untouched."""
    rows = db.scalars(select(TaskProgress).where(TaskProgress.user_id == user.id))
    return {row.task_id: row for row in rows}


def get_or_create_progress(db: Session, user: User, task: Task) -> TaskProgress:
    row = db.get(TaskProgress, task.id)
    if row is None:
        # A row appears only when a task is first touched; absent means
        # untouched, not "explicitly zero".
        row = TaskProgress(task_id=task.id, user_id=user.id)
        db.add(row)
        db.flush()
    return row


def leaf_tasks(day: Day) -> list[Task]:
    """The tasks that count towards progress: subtasks, or childless mains."""
    leaves: list[Task] = []
    for task in day.tasks:
        if task.parent_id is not None:
            continue
        if task.subtasks:
            leaves.extend(task.subtasks)
        else:
            leaves.append(task)
    return leaves


def is_completed(task: Task, progress: dict[uuid.UUID, TaskProgress]) -> bool:
    """A main task is complete when all of its subtasks are."""
    if task.subtasks:
        return all(is_completed(sub, progress) for sub in task.subtasks)
    row = progress.get(task.id)
    return bool(row and row.completed)


def task_status(task: Task, progress: dict[uuid.UUID, TaskProgress]) -> str:
    """One of "not-started", "in-progress" or "completed".

    A main task reflects its subtasks: complete when they all are, in progress
    as soon as any of them has been started or finished. A leaf task is in
    progress once Start has been pressed and it is not yet done.
    """
    if task.subtasks:
        states = [task_status(sub, progress) for sub in task.subtasks]
        if all(s == "completed" for s in states):
            return "completed"
        return "in-progress" if any(s != "not-started" for s in states) else "not-started"

    row = progress.get(task.id)
    if row and row.completed:
        return "completed"
    if row and row.started_at is not None:
        return "in-progress"
    return "not-started"


def minutes_for(task: Task, progress: dict[uuid.UUID, TaskProgress]) -> int:
    """Time on a task, plus everything beneath it."""
    row = progress.get(task.id)
    total = row.minutes_spent if row else 0
    return total + sum(minutes_for(sub, progress) for sub in task.subtasks)


# --- positions ----------------------------------------------------------


def next_day_position(db: Session, user: User) -> int:
    positions = list(db.scalars(select(Day.position).where(Day.user_id == user.id)))
    return max(positions, default=0) + 1


def siblings(db: Session, day: Day, parent_id: uuid.UUID | None) -> list[Task]:
    """Tasks at one level, read from the database rather than the relationship.

    `day.tasks` can be stale part-way through a multi-insert (restoring a day,
    for instance), which would hand every new row position 1.
    """
    db.flush()
    stmt = select(Task).where(Task.day_id == day.id)
    stmt = stmt.where(Task.parent_id.is_(None) if parent_id is None else Task.parent_id == parent_id)
    return list(db.scalars(stmt.order_by(Task.position)))


def next_task_position(db: Session, day: Day, parent_id: uuid.UUID | None) -> int:
    existing = siblings(db, day, parent_id)
    return max((t.position for t in existing), default=0) + 1


def insert_day(db: Session, user: User, title: str, position: int | None) -> Day:
    """Append a day, or insert it at `position`, shifting later days down."""
    last = next_day_position(db, user)
    if position is None or position >= last:
        target = last
    else:
        target = position
        # Shift from the end backwards so positions stay unique as we go.
        to_shift = db.scalars(
            select(Day)
            .where(Day.user_id == user.id, Day.position >= target)
            .order_by(Day.position.desc())
        )
        for day in to_shift:
            day.position += 1

    day = Day(user_id=user.id, position=target, title=title)
    db.add(day)
    db.flush()
    return day


def compact_day_positions(db: Session, user: User) -> None:
    """Renumber days 1..n after a delete, so there are never gaps."""
    days = db.scalars(select(Day).where(Day.user_id == user.id).order_by(Day.position)).all()
    for index, day in enumerate(days, start=1):
        if day.position != index:
            day.position = index


def compact_task_positions(db: Session, day: Day, parent_id: uuid.UUID | None) -> None:
    for index, task in enumerate(siblings(db, day, parent_id), start=1):
        task.position = index


def apply_order(items: dict[uuid.UUID, Task], ordered_ids: list[uuid.UUID]) -> None:
    """Rewrite `position` to match `ordered_ids`.

    Taking the whole ordered list (rather than a from/to index pair) keeps
    this race-free: the client's view of the order wins, in one transaction.
    """
    for index, item_id in enumerate(ordered_ids, start=1):
        items[item_id].position = index


def insert_task(
    db: Session,
    day: Day,
    parent: Task | None,
    title: str,
    position: int | None = None,
    completed: bool = False,
    notes: str = "",
    minutes_spent: int = 0,
) -> Task:
    """Create a task, optionally at a position and with existing progress.

    The progress arguments are what let a deleted task be restored intact.
    """
    parent_id = parent.id if parent else None
    existing = siblings(db, day, parent_id)
    target = len(existing) + 1 if position is None else min(position, len(existing) + 1)

    for task in existing:
        if task.position >= target:
            task.position += 1

    task = Task(
        day_id=day.id,
        parent_id=parent_id,
        title=title,
        position=target,
        original_day_position=day.position,
    )
    db.add(task)
    db.flush()

    if completed or notes or minutes_spent:
        db.add(
            TaskProgress(
                task_id=task.id,
                user_id=day.user_id,
                completed=completed,
                notes=notes,
                minutes_spent=minutes_spent,
            )
        )
    return task


# --- deleting -----------------------------------------------------------


def delete_impact(db: Session, day: Day) -> tuple[int, int, int]:
    """(task count, completed count, minutes) that deleting this day removes."""
    progress = {
        row.task_id: row
        for row in db.scalars(
            select(TaskProgress).where(
                TaskProgress.task_id.in_([t.id for t in day.tasks] or [uuid.uuid4()])
            )
        )
    }
    leaves = leaf_tasks(day)
    completed = sum(1 for t in leaves if progress.get(t.id) and progress[t.id].completed)
    minutes = sum(row.minutes_spent for row in progress.values())
    return len(leaves), completed, minutes


# --- carrying work forward ----------------------------------------------


def carry_forward(
    db: Session, user: User, day: Day, target: Day, task_ids: list[uuid.UUID]
) -> list[uuid.UUID]:
    """Move chosen unfinished tasks to `target`, returning the ids that moved.

    Moving rather than copying keeps the plan honest: the work appears once,
    on the day it is actually planned for. Because the rows themselves move,
    notes and recorded time travel with them.

    A subtask moved on its own is placed under a main task of the same name on
    the target day, created if it is not already there — so "AWS CloudOps"
    simply continues tomorrow rather than the subtask being orphaned. A main
    task without subtasks does the same when the target already has a main task
    of that name.
    """
    progress = progress_by_task(db, user)
    chosen = {t.id: t for t in day.tasks if t.id in set(task_ids)}

    # Never relocate finished work, even if it was selected.
    moving = [t for t in chosen.values() if not is_completed(t, progress)]
    # If a main task is moving, its subtasks travel with it; listing them
    # separately would try to move them twice.
    moving_ids = {t.id for t in moving}
    moving = [t for t in moving if t.parent_id not in moving_ids]
    if not moving:
        return []

    # Moving work to an earlier day is catching up, not slipping, so it adds
    # nothing to the carried-forward history.
    forward = target.position > day.position
    now = datetime.now(timezone.utc)
    moved: list[uuid.UUID] = []
    parent_cache: dict[str, Task] = {}

    def same_named_main(title: str) -> Task | None:
        return next(
            (t for t in target.tasks if t.parent_id is None and t.title == title), None
        )

    for task in sorted(moving, key=lambda t: (t.parent_id is not None, t.position)):
        # A main task whose name already exists on the target day merges into
        # it, rather than leaving the day with two "Kubernetes" headings.
        if task.parent_id is None and task.subtasks:
            existing_main = same_named_main(task.title)
            if existing_main is not None:
                for sub in list(task.subtasks):
                    if is_completed(sub, progress):
                        continue
                    sub.day_id = target.id
                    sub.parent_id = existing_main.id
                    sub.position = next_task_position(db, target, existing_main.id)
                    if forward:
                        sub.carried_count += 1
                        sub.last_carried_from = day.position
                        sub.last_carried_at = now
                        if sub.original_day_position is None:
                            sub.original_day_position = day.position
                    moved.append(sub.id)
                db.flush()
                # The heading it left behind is now empty, so remove it.
                db.refresh(task)
                if not task.subtasks:
                    db.delete(task)
                    db.flush()
                continue

        if task.parent_id is None:
            # A main task with no subtasks of its own, carried to a day that
            # already has a heading of that name, becomes a subtask of it
            # instead of a second, duplicate heading.
            new_parent = None if task.subtasks else same_named_main(task.title)
        else:
            # Re-home the subtask under a same-named main task on the target.
            source_parent = db.get(Task, task.parent_id)
            name = source_parent.title if source_parent else "Carried forward"
            if name in parent_cache:
                new_parent = parent_cache[name]
            else:
                new_parent = next(
                    (t for t in target.tasks if t.parent_id is None and t.title == name), None
                )
                if new_parent is None:
                    new_parent = insert_task(db, target, None, name)
                parent_cache[name] = new_parent

        task.day_id = target.id
        task.parent_id = new_parent.id if new_parent else None
        task.position = next_task_position(db, target, task.parent_id)
        if forward:
            task.carried_count += 1
            task.last_carried_from = day.position
            task.last_carried_at = now
            if task.original_day_position is None:
                task.original_day_position = day.position

        # Subtasks follow their parent to the new day.
        for sub in task.subtasks:
            sub.day_id = target.id
            if forward:
                sub.carried_count += 1
                sub.last_carried_from = day.position
                sub.last_carried_at = now
                if sub.original_day_position is None:
                    sub.original_day_position = day.position

        moved.append(task.id)

    db.flush()
    db.refresh(day)

    # Close the gaps left behind, and drop main tasks that are now empty
    # shells because every subtask moved on.
    for parent_id in {None} | {t.id for t in day.tasks if t.parent_id is None}:
        compact_task_positions(db, day, parent_id)

    return moved


def move_tasks(db: Session, tasks: list[Task], target: Day) -> None:
    """Move specific tasks to a day. This is how a carry-forward is undone."""
    sources = {t.day_id for t in tasks}
    parent_cache: dict[str, Task] = {}

    for task in tasks:
        # Only undoing a move to a later day has history to roll back.
        origin = db.get(Day, task.day_id)
        undoes_carry = origin is not None and target.position < origin.position
        if task.parent_id is None:
            new_parent_id = None
        else:
            source_parent = db.get(Task, task.parent_id)
            name = source_parent.title if source_parent else "Carried forward"
            cached = parent_cache.get(name)
            if cached is None:
                cached = next(
                    (t for t in target.tasks if t.parent_id is None and t.title == name), None
                )
                if cached is None:
                    cached = insert_task(db, target, None, name)
                parent_cache[name] = cached
            new_parent_id = cached.id

        task.day_id = target.id
        task.parent_id = new_parent_id
        task.position = next_task_position(db, target, new_parent_id)
        # Undoing a carry-forward should also undo its history entry.
        if undoes_carry:
            task.carried_count = max(0, task.carried_count - 1)
        for sub in task.subtasks:
            sub.day_id = target.id
            if undoes_carry:
                sub.carried_count = max(0, sub.carried_count - 1)

    db.flush()
    for day_id in sources:
        if day_id == target.id:
            continue
        source = db.get(Day, day_id)
        if source is None:
            continue
        for parent_id in {None} | {t.id for t in source.tasks if t.parent_id is None}:
            compact_task_positions(db, source, parent_id)


# --- time ---------------------------------------------------------------


def stop_timer(row: TaskProgress, now: datetime | None = None) -> int:
    """Fold a running timer into the total, returning the minutes added."""
    if row.timer_started_at is None:
        return 0
    now = now or datetime.now(timezone.utc)
    started = row.timer_started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = max(0, int((now - started).total_seconds() // 60))
    row.minutes_spent += elapsed
    row.timer_started_at = None
    return elapsed


# --- the deletion log ---------------------------------------------------


def log_deletion(
    db: Session, user: User, task: Task, progress: dict[uuid.UUID, TaskProgress], reason: str
) -> DeletedTask:
    """Record that a task was removed, before the row disappears.

    Details are copied rather than referenced: the day may be deleted too, so
    a foreign key would leave nothing readable behind.
    """
    parent = db.get(Task, task.parent_id) if task.parent_id else None
    day = db.get(Day, task.day_id)
    entry = DeletedTask(
        user_id=user.id,
        title=task.title,
        day_position=day.position if day else None,
        day_title=day.title if day else "",
        parent_title=parent.title if parent else None,
        was_completed=is_completed(task, progress),
        minutes_spent=minutes_for(task, progress),
        subtask_count=len(task.subtasks),
        reason=reason,
    )
    db.add(entry)
    return entry


def log_day_deletion(db: Session, user: User, day: Day) -> list[DeletedTask]:
    """Log every main task on a day that is about to be removed."""
    progress = progress_by_task(db, user)
    return [
        log_deletion(db, user, task, progress, reason="day")
        for task in day.tasks
        if task.parent_id is None
    ]
