"""Signup, login, "who am I", and password reset.

Signup also clones the default plan.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.config import settings
from app.deps import CurrentUser, DbSession
from app.models import Day, PasswordResetToken, Task, TaskProgress, User, UserSettings
from app.schemas import (
    AccountSummaryOut,
    ChangePasswordIn,
    Credentials,
    DeleteAccountIn,
    ForgotPasswordIn,
    ResetPasswordIn,
    TokenOut,
    UserOut,
)
from app.security import (
    create_access_token,
    hash_password,
    hash_reset_token,
    new_reset_token,
    reset_token_expiry,
    verify_password,
)

log = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(body: Credentials, db: DbSession) -> TokenOut:
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="That email is already registered")

    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()

    # No plan yet: the account chooses one on the setup screen, so it can
    # start from the default, an upload, or a blank set of days.
    db.add(UserSettings(user_id=user.id, onboarded=False))
    db.commit()

    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(body: Credentials, db: DbSession) -> TokenOut:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    # Same message either way, so this cannot be used to discover which
    # emails have accounts.
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


# --- password reset -----------------------------------------------------


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(body: ForgotPasswordIn, db: DbSession) -> dict[str, str]:
    """Start a password reset.

    Always returns the same response, whether or not the email is registered,
    so this cannot be used to discover which addresses have accounts.

    There is no mail server here, so the reset link is written to the API log
    (`docker-compose logs api`). Swap the log line below for an email send when
    you have SMTP.
    """
    email = body.email.lower()
    user = db.scalar(select(User).where(User.email == email))

    if user is not None:
        # Invalidate any earlier outstanding tokens for this account, so only
        # the newest link works.
        for old in db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        ):
            old.used_at = datetime.now(timezone.utc)

        token, token_hash = new_reset_token()
        db.add(
            PasswordResetToken(
                user_id=user.id, token_hash=token_hash, expires_at=reset_token_expiry()
            )
        )
        db.commit()

        origin = settings.cors_origin_list[0] if settings.cors_origin_list else ""
        log.warning(
            "Password reset requested for %s — link valid for 30 minutes:\n    %s/reset-password?token=%s",
            email,
            origin,
            token,
        )

    return {
        "detail": (
            "If that email has an account, a reset link has been generated. "
            "With no mail server configured, it is printed in the API log."
        )
    }


@router.post("/reset-password", response_model=TokenOut)
def reset_password(body: ResetPasswordIn, db: DbSession) -> TokenOut:
    """Complete a reset. The token is single-use and expires after 30 minutes."""
    row = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_reset_token(body.token)
        )
    )
    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None or row.expires_at <= now:
        raise HTTPException(
            status_code=400, detail="That reset link is invalid or has expired. Request a new one."
        )

    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="That reset link is no longer valid.")

    user.password_hash = hash_password(body.password)
    row.used_at = now
    db.commit()

    # Sign them straight in, so a reset does not end at another login form.
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: ChangePasswordIn, user: CurrentUser, db: DbSession) -> None:
    """Change the password of the signed-in user, confirming the current one."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Your current password is not correct")

    user.password_hash = hash_password(body.new_password)
    db.commit()


# --- deleting an account ------------------------------------------------


@router.get("/account-summary", response_model=AccountSummaryOut)
def account_summary(user: CurrentUser, db: DbSession) -> AccountSummaryOut:
    """What a deletion would destroy, so the warning can be specific."""
    days = db.scalar(select(func.count()).select_from(Day).where(Day.user_id == user.id)) or 0
    tasks = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .join(Day, Task.day_id == Day.id)
            .where(Day.user_id == user.id)
        )
        or 0
    )
    completed = (
        db.scalar(
            select(func.count())
            .select_from(TaskProgress)
            .where(TaskProgress.user_id == user.id, TaskProgress.completed.is_(True))
        )
        or 0
    )
    notes = (
        db.scalar(
            select(func.count())
            .select_from(TaskProgress)
            .where(TaskProgress.user_id == user.id, TaskProgress.notes != "")
        )
        or 0
    )
    minutes = (
        db.scalar(
            select(func.coalesce(func.sum(TaskProgress.minutes_spent), 0)).where(
                TaskProgress.user_id == user.id
            )
        )
        or 0
    )
    return AccountSummaryOut(
        email=user.email,
        days=days,
        tasks=tasks,
        completed_tasks=completed,
        notes=notes,
        minutes_spent=minutes,
    )


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(body: DeleteAccountIn, user: CurrentUser, db: DbSession) -> None:
    """Permanently delete the signed-in account and everything it owns.

    This cannot be undone: the plan, all progress and all notes go with it.
    Two guards before that happens — the current password, and typing the
    account's own email.
    """
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail="That password is not correct")
    if body.confirm_email.lower() != user.email:
        raise HTTPException(
            status_code=400, detail="The email you typed does not match this account"
        )

    # Days, topics, progress, settings and reset tokens all cascade from here.
    db.delete(user)
    db.commit()
