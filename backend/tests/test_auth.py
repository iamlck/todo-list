"""Signup, login, setup, and access control."""


def test_signup_leaves_the_account_without_a_plan(client):
    response = client.post(
        "/auth/signup", json={"email": "new@example.com", "password": "password123"}
    )
    assert response.status_code == 201
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    plan = client.get("/me/plan", headers=headers).json()
    # The setup screen chooses the plan, so a fresh account starts empty.
    assert plan["onboarded"] is False
    assert plan["days"] == []


def test_default_setup_creates_the_twenty_day_plan(client, register):
    headers = register()
    plan = client.get("/me/plan", headers=headers).json()

    assert plan["onboarded"] is True
    assert len(plan["days"]) == 20
    assert plan["days"][-1]["title"] == "Exam and wrap-up"

    day_one = plan["days"][0]
    assert [t["title"] for t in day_one["tasks"]] == ["AWS CloudOps", "Kubernetes", "GenAI"]
    assert all(t["subtasks"] for t in day_one["tasks"])
    assert not any(t["completed"] for t in day_one["tasks"])


def test_setup_is_refused_once_a_plan_exists(client, register):
    headers = register()
    response = client.post("/me/plan/setup", json={"mode": "default"}, headers=headers)
    assert response.status_code == 409


def test_blank_setup_creates_empty_days(client, register):
    headers = register(plan=False)
    client.post("/me/plan/setup", json={"mode": "blank", "day_count": 7}, headers=headers)

    plan = client.get("/me/plan", headers=headers).json()
    assert len(plan["days"]) == 7
    assert all(d["tasks"] == [] for d in plan["days"])


def test_import_setup_builds_the_uploaded_plan(client, register):
    headers = register(plan=False)
    payload = {
        "mode": "import",
        "days": [
            {
                "title": "Week one",
                "tasks": [
                    {"title": "Terraform", "subtasks": ["Modules", "State"]},
                    {"title": "Reading", "subtasks": []},
                ],
            },
            {"title": "Week two", "tasks": [{"title": "Practice", "subtasks": ["Lab 1"]}]},
        ],
    }
    assert client.post("/me/plan/setup", json=payload, headers=headers).status_code == 201

    days = client.get("/me/plan", headers=headers).json()["days"]
    assert [d["title"] for d in days] == ["Week one", "Week two"]
    assert [t["title"] for t in days[0]["tasks"]] == ["Terraform", "Reading"]
    assert [s["title"] for s in days[0]["tasks"][0]["subtasks"]] == ["Modules", "State"]


def test_duplicate_email_is_rejected(client):
    body = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/auth/signup", json=body).status_code == 201
    assert client.post("/auth/signup", json=body).status_code == 409


def test_login_succeeds_and_wrong_password_fails(client):
    body = {"email": "u@example.com", "password": "password123"}
    client.post("/auth/signup", json=body)

    assert client.post("/auth/login", json=body).status_code == 200
    assert client.post("/auth/login", json={**body, "password": "wrongpassword"}).status_code == 401


def test_plan_requires_authentication(client):
    assert client.get("/me/plan").status_code == 401
    assert client.get("/me/plan", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_users_cannot_reach_each_others_tasks(client, register):
    alice = register("alice@example.com")
    bob = register("bob@example.com")

    task = client.get("/me/plan", headers=alice).json()["days"][0]["tasks"][0]["subtasks"][0]["id"]

    # 404 rather than 403, so Bob cannot even confirm it exists.
    assert client.put(
        f"/me/progress/{task}", json={"completed": True}, headers=bob
    ).status_code == 404
    assert client.patch(
        f"/me/tasks/{task}", json={"title": "hijacked"}, headers=bob
    ).status_code == 404


def test_each_user_gets_an_independent_copy(client, register):
    alice = register("alice@example.com")
    bob = register("bob@example.com")

    day = client.get("/me/plan", headers=alice).json()["days"][0]
    client.patch(f"/me/days/{day['id']}", json={"title": "Alice only"}, headers=alice)

    assert client.get("/me/plan", headers=bob).json()["days"][0]["title"] == "Foundations"
