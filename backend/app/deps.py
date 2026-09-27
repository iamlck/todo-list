"""Shared FastAPI dependencies: the current user, and ownership-checked lookups."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Day, Task, User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise unauthorized
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise unauthorized

    user = db.get(User, user_uuid)
    if user is None:
        raise unauthorized
    return user


def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Guards the admin area.

    404 rather than 403, so the admin routes are invisible to accounts that
    are not administrators.
    """
    if not user.is_admin:
        raise HTTPException(status_code=404, detail="Not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
DbSession = Annotated[Session, Depends(get_db)]


def get_owned_day(db: Session, user: User, day_id: uuid.UUID) -> Day:
    """Fetch a day, or 404 if it does not exist *or* belongs to someone else.

    Returning 404 rather than 403 avoids revealing that another user's day
    exists.
    """
    day = db.scalar(select(Day).where(Day.id == day_id, Day.user_id == user.id))
    if day is None:
        raise HTTPException(status_code=404, detail="Day not found")
    return day


def get_owned_task(db: Session, user: User, task_id: uuid.UUID) -> Task:
    """Fetch a task via its day, enforcing that the day belongs to this user."""
    task = db.scalar(
        select(Task).join(Day, Task.day_id == Day.id).where(
            Task.id == task_id, Day.user_id == user.id
        )
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
