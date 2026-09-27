"""The admin area: listing, granting rights, and removing accounts."""

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User


def make_admin(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        user.is_admin = True
        db.commit()


@pytest.fixture
def admin(client, register):
    headers = register("admin@example.com", "password123", plan=False)
    make_admin("admin@example.com")
    return headers


def test_admin_routes_are_invisible_to_ordinary_accounts(client, register):
    headers = register(plan=False)
    # 404 rather than 403: the area should not announce itself.
    assert client.get("/admin/users", headers=headers).status_code == 404
    assert client.get("/admin/users").status_code == 401


def test_admin_can_list_users_with_their_plan_size(client, register, admin):
    register("learner@example.com")
    task = client.get("/me/plan", headers=admin).json()

    rows = client.get("/admin/users", headers=admin).json()
    by_email = {r["email"]: r for r in rows}
    assert set(by_email) == {"admin@example.com", "learner@example.com"}

    learner = by_email["learner@example.com"]
    assert learner["onboarded"] is True
    assert learner["days"] == 20
    assert learner["tasks"] > 0
    assert by_email["admin@example.com"]["is_admin"] is True
    assert by_email["admin@example.com"]["onboarded"] is False
    assert task is not None


def test_counts_are_not_inflated_by_joins(client, register, admin):
    headers = register("counts@example.com")
    plan = client.get("/me/plan", headers=headers).json()
    leaves = [s for d in plan["days"] for t in d["tasks"] for s in (t["subtasks"] or [t])]
    client.put(f"/me/progress/{leaves[0]['id']}", json={"completed": True}, headers=headers)
    client.put(f"/me/progress/{leaves[0]['id']}/time", json={"minutes_spent": 30}, headers=headers)

    row = next(
        r for r in client.get("/admin/users", headers=admin).json()
        if r["email"] == "counts@example.com"
    )
    assert row["days"] == 20
    assert row["completed_tasks"] == 1
    assert row["minutes_spent"] == 30


def test_search_filters_by_email(client, register, admin):
    register("alice@example.com")
    register("bob@example.com")

    rows = client.get("/admin/users", params={"q": "alice"}, headers=admin).json()
    assert [r["email"] for r in rows] == ["alice@example.com"]


def test_admin_can_grant_and_withdraw_rights(client, register, admin):
    register("promote@example.com", plan=False)
    rows = client.get("/admin/users", headers=admin).json()
    target = next(r for r in rows if r["email"] == "promote@example.com")

    granted = client.patch(f"/admin/users/{target['id']}", json={"is_admin": True}, headers=admin)
    assert granted.status_code == 200
    assert granted.json()["is_admin"] is True

    withdrawn = client.patch(
        f"/admin/users/{target['id']}", json={"is_admin": False}, headers=admin
    )
    assert withdrawn.json()["is_admin"] is False


def test_an_admin_cannot_remove_their_own_rights(client, admin):
    me = next(
        r for r in client.get("/admin/users", headers=admin).json()
        if r["email"] == "admin@example.com"
    )
    response = client.patch(f"/admin/users/{me['id']}", json={"is_admin": False}, headers=admin)
    assert response.status_code == 400


def test_the_last_administrator_cannot_be_withdrawn(client, register, admin):
    # A second admin, withdrawn by the first, leaving exactly one.
    register("second@example.com", plan=False)
    rows = client.get("/admin/users", headers=admin).json()
    second = next(r for r in rows if r["email"] == "second@example.com")
    client.patch(f"/admin/users/{second['id']}", json={"is_admin": True}, headers=admin)

    # Now the second admin tries to withdraw the first, then themselves.
    token = client.post(
        "/auth/login", json={"email": "second@example.com", "password": "password123"}
    ).json()["access_token"]
    second_headers = {"Authorization": f"Bearer {token}"}
    first = next(
        r for r in client.get("/admin/users", headers=admin).json()
        if r["email"] == "admin@example.com"
    )
    assert client.patch(
        f"/admin/users/{first['id']}", json={"is_admin": False}, headers=second_headers
    ).status_code == 200
    # Only one left, so this must be refused.
    assert client.patch(
        f"/admin/users/{second['id']}", json={"is_admin": False}, headers=second_headers
    ).status_code == 400


def test_deleting_a_user_needs_the_admins_password_and_their_email(client, register, admin):
    register("victim@example.com")
    target = next(
        r for r in client.get("/admin/users", headers=admin).json()
        if r["email"] == "victim@example.com"
    )

    assert client.request(
        "DELETE", f"/admin/users/{target['id']}",
        json={"password": "wrongpass1", "confirm_email": "victim@example.com"}, headers=admin,
    ).status_code == 400
    assert client.request(
        "DELETE", f"/admin/users/{target['id']}",
        json={"password": "password123", "confirm_email": "other@example.com"}, headers=admin,
    ).status_code == 400
    # Untouched after both refusals.
    assert any(
        r["email"] == "victim@example.com" for r in client.get("/admin/users", headers=admin).json()
    )


def test_deleting_a_user_removes_everything_they_own(client, register, admin):
    from sqlalchemy import func

    from app.models import Day, Task, TaskProgress

    headers = register("gone@example.com")
    plan = client.get("/me/plan", headers=headers).json()
    leaf = next(s for d in plan["days"] for t in d["tasks"] for s in (t["subtasks"] or [t]))
    client.put(f"/me/progress/{leaf['id']}", json={"completed": True}, headers=headers)

    target = next(
        r for r in client.get("/admin/users", headers=admin).json()
        if r["email"] == "gone@example.com"
    )
    response = client.request(
        "DELETE", f"/admin/users/{target['id']}",
        json={"password": "password123", "confirm_email": "gone@example.com"}, headers=admin,
    )
    assert response.status_code == 204

    assert client.get("/me/plan", headers=headers).status_code == 401
    with SessionLocal() as db:
        # The admin has no plan, so nothing of either should remain.
        assert db.scalar(select(func.count()).select_from(Day)) == 0
        assert db.scalar(select(func.count()).select_from(Task)) == 0
        assert db.scalar(select(func.count()).select_from(TaskProgress)) == 0


def test_an_admin_deletes_their_own_account_from_the_account_page(client, admin):
    me = next(
        r for r in client.get("/admin/users", headers=admin).json()
        if r["email"] == "admin@example.com"
    )
    response = client.request(
        "DELETE", f"/admin/users/{me['id']}",
        json={"password": "password123", "confirm_email": "admin@example.com"}, headers=admin,
    )
    assert response.status_code == 400


def test_signup_never_creates_an_administrator(client):
    response = client.post(
        "/auth/signup", json={"email": "plain@example.com", "password": "password123"}
    )
    assert response.json()["user"]["is_admin"] is False
