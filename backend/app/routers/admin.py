"""Administration: listing and removing user accounts.

Every route here depends on `CurrentAdmin`, which 404s for ordinary accounts,
so the admin area is invisible rather than merely forbidden.

Administrators see counts and totals per account, never the contents of
someone's notes — knowing how much work an account holds is enough to
administer it.
"""

import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from app.deps import CurrentAdmin, DbSession
from app.models import Day, Task, TaskProgress, User, UserSettings
from app.schemas import AdminDeleteIn, AdminUserOut, AdminUserUpdate
from app.security import verify_password

router = APIRouter(prefix="/admin", tags=["admin"])


def _serialize(row) -> AdminUserOut:
    user, settings, days, tasks, completed, minutes, last_activity = row
    return AdminUserOut(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        created_at=user.created_at,
        onboarded=bool(settings and settings.onboarded),
        start_date=settings.start_date if settings else None,
        days=days or 0,
        tasks=tasks or 0,
        completed_tasks=completed or 0,
        minutes_spent=minutes or 0,
        last_activity=last_activity,
    )


def _users_query(db: DbSession):
    """Each user with their plan size and activity, as scalar subqueries.

    Subqueries rather than joins: joining days and progress in one statement
    would multiply the rows and inflate every count.
    """
    day_count = (
        select(func.count()).select_from(Day).where(Day.user_id == User.id).scalar_subquery()
    )
    task_count = (
        select(func.count())
        .select_from(Task)
        .join(Day, Task.day_id == Day.id)
        .where(Day.user_id == User.id)
        .scalar_subquery()
    )
    completed_count = (
        select(func.count())
        .select_from(TaskProgress)
        .where(TaskProgress.user_id == User.id, TaskProgress.completed.is_(True))
        .scalar_subquery()
    )
    minutes = (
        select(func.coalesce(func.sum(TaskProgress.minutes_spent), 0))
        .where(TaskProgress.user_id == User.id)
        .scalar_subquery()
    )
    last_activity = (
        select(func.max(TaskProgress.updated_at))
        .where(TaskProgress.user_id == User.id)
        .scalar_subquery()
    )
    return select(
        User, UserSettings, day_count, task_count, completed_count, minutes, last_activity
    ).outerjoin(UserSettings, UserSettings.user_id == User.id)


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    admin: CurrentAdmin, db: DbSession, q: str | None = None, limit: int = 200
) -> list[AdminUserOut]:
    """All accounts, newest first. `q` filters by email."""
    stmt = _users_query(db)
    if q:
        stmt = stmt.where(User.email.ilike(f"%{q.strip().lower()}%"))
    rows = db.execute(stmt.order_by(User.created_at.desc()).limit(min(limit, 500))).all()
    return [_serialize(r) for r in rows]


@router.get("/users/{user_id}", response_model=AdminUserOut)
def get_user(user_id: uuid.UUID, admin: CurrentAdmin, db: DbSession) -> AdminUserOut:
    row = db.execute(_users_query(db).where(User.id == user_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize(row)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def set_admin(
    user_id: uuid.UUID, body: AdminUserUpdate, admin: CurrentAdmin, db: DbSession
) -> AdminUserOut:
    """Grant or withdraw administrator rights."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not body.is_admin:
        if target.id == admin.id:
            # Removing your own rights would lock you out mid-session.
            raise HTTPException(
                status_code=400, detail="You cannot remove your own administrator rights"
            )
        remaining = db.scalar(
            select(func.count()).select_from(User).where(User.is_admin.is_(True))
        )
        if remaining <= 1:
            raise HTTPException(status_code=400, detail="There must be at least one administrator")

    target.is_admin = body.is_admin
    db.commit()

    return _serialize(db.execute(_users_query(db).where(User.id == user_id)).first())


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: uuid.UUID, body: AdminDeleteIn, admin: CurrentAdmin, db: DbSession
) -> Response:
    """Permanently delete another account and everything it owns.

    Guarded the same way as deleting your own: the administrator's password,
    plus typing the target's email. There is no undo.
    """
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id:
        # Deleting yourself belongs on the account page, where the wording is
        # about your own data.
        raise HTTPException(
            status_code=400, detail="Delete your own account from the Account page"
        )
    if not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Your password is not correct")
    if body.confirm_email.lower() != target.email:
        raise HTTPException(
            status_code=400, detail="The email you typed does not match that account"
        )

    db.delete(target)  # cascades to their plan, progress, history and tokens
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
