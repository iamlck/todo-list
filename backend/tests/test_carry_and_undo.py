"""Carrying work forward, undoing it, and deleting an account."""


def plan(client, headers):
    return client.get("/me/plan", headers=headers).json()


def leaves(day):
    return [s for t in day["tasks"] for s in (t["subtasks"] or [t])]


# --- carry forward ------------------------------------------------------


def test_carry_forward_moves_unfinished_work_to_the_next_day(client, register):
    headers = register()
    before = plan(client, headers)["days"]
    day1 = before[0]

    result = client.post(f"/me/days/{day1['id']}/carry-forward", json={}, headers=headers).json()
    assert result["target_day_position"] == 2
    assert result["moved"] > 0

    after = plan(client, headers)["days"]
    assert leaves(after[0]) == []
    assert len(leaves(after[1])) == len(leaves(day1)) + len(leaves(before[1]))


def test_carried_work_merges_into_a_task_of_the_same_name(client, register):
    headers = register()
    day1 = plan(client, headers)["days"][0]

    client.post(f"/me/days/{day1['id']}/carry-forward", json={}, headers=headers)

    day2 = plan(client, headers)["days"][1]
    titles = [t["title"] for t in day2["tasks"]]
    # No duplicate headings: "Kubernetes" appears once, not twice.
    assert len(titles) == len(set(titles))


def test_only_the_chosen_tasks_move(client, register):
    headers = register()
    day1 = plan(client, headers)["days"][0]
    all_leaves = leaves(day1)
    chosen = [t["id"] for t in all_leaves[:2]]

    result = client.post(
        f"/me/days/{day1['id']}/carry-forward", json={"task_ids": chosen}, headers=headers
    ).json()
    assert result["moved"] == 2

    remaining = {t["id"] for t in leaves(plan(client, headers)["days"][0])}
    assert remaining == {t["id"] for t in all_leaves[2:]}


def test_finished_work_is_never_carried_even_if_selected(client, register):
    headers = register()
    day1 = plan(client, headers)["days"][0]
    done = leaves(day1)[0]
    client.put(f"/me/progress/{done['id']}", json={"completed": True}, headers=headers)

    result = client.post(
        f"/me/days/{day1['id']}/carry-forward",
        json={"task_ids": [done["id"], leaves(day1)[1]["id"]]},
        headers=headers,
    ).json()

    assert result["moved"] == 1
    assert any(t["id"] == done["id"] for t in leaves(plan(client, headers)["days"][0]))


def test_carry_forward_records_its_history(client, register):
    headers = register()
    day1 = plan(client, headers)["days"][0]
    chosen = leaves(day1)[0]

    client.post(
        f"/me/days/{day1['id']}/carry-forward", json={"task_ids": [chosen["id"]]}, headers=headers
    )

    moved = next(t for t in leaves(plan(client, headers)["days"][1]) if t["id"] == chosen["id"])
    assert moved["carried_count"] == 1
    assert moved["last_carried_from"] == 1
    assert moved["original_day_position"] == 1


def test_carry_forward_takes_notes_and_time_with_it(client, register):
    headers = register()
    day1 = plan(client, headers)["days"][0]
    task = leaves(day1)[0]
    client.put(f"/me/progress/{task['id']}/notes", json={"notes": "half done"}, headers=headers)
    client.put(f"/me/progress/{task['id']}/time", json={"minutes_spent": 35}, headers=headers)

    client.post(
        f"/me/days/{day1['id']}/carry-forward", json={"task_ids": [task["id"]]}, headers=headers
    )

    moved = next(t for t in leaves(plan(client, headers)["days"][1]) if t["id"] == task["id"])
    assert moved["notes"] == "half done"
    assert moved["minutes_spent"] == 35


def test_carry_forward_refusals(client, register):
    headers = register()
    days = plan(client, headers)["days"]
    day1, last = days[0], days[-1]

    assert client.post(
        f"/me/days/{day1['id']}/carry-forward", json={"task_ids": []}, headers=headers
    ).status_code == 400
    assert client.post(
        f"/me/days/{day1['id']}/carry-forward",
        json={"task_ids": [leaves(days[3])[0]["id"]]},
        headers=headers,
    ).status_code == 400
    assert client.post(
        f"/me/days/{last['id']}/carry-forward", json={}, headers=headers
    ).status_code == 400
    assert client.post(
        f"/me/days/{day1['id']}/carry-forward",
        json={"target_day_id": day1["id"]},
        headers=headers,
    ).status_code == 400


# --- undo ---------------------------------------------------------------


def test_carry_forward_can_be_undone(client, register):
    headers = register()
    day1 = plan(client, headers)["days"][0]
    before = len(leaves(day1))

    result = client.post(f"/me/days/{day1['id']}/carry-forward", json={}, headers=headers).json()
    response = client.post(
        "/me/tasks/move",
        json={"task_ids": result["moved_task_ids"], "target_day_id": day1["id"]},
        headers=headers,
    )
    assert response.status_code == 204

    after = plan(client, headers)["days"][0]
    assert len(leaves(after)) == before
    # Undoing the move also undoes the history entry it added.
    assert all(t["carried_count"] == 0 for t in leaves(after))


def test_tasks_cannot_be_moved_into_another_users_day(client, register):
    alice = register("alice@example.com")
    bob = register("bob@example.com")

    alice_task = leaves(plan(client, alice)["days"][0])[0]["id"]
    bob_day = plan(client, bob)["days"][0]["id"]

    assert client.post(
        "/me/tasks/move",
        json={"task_ids": [alice_task], "target_day_id": bob_day},
        headers=bob,
    ).status_code == 404


def test_a_deleted_task_can_be_restored_with_everything_on_it(client, register):
    headers = register()
    day = plan(client, headers)["days"][0]
    main = day["tasks"][0]
    sub = main["subtasks"][0]
    client.put(f"/me/progress/{sub['id']}", json={"completed": True}, headers=headers)
    client.put(f"/me/progress/{sub['id']}/time", json={"minutes_spent": 20}, headers=headers)
    client.put(f"/me/progress/{sub['id']}/notes", json={"notes": "keep"}, headers=headers)

    saved = plan(client, headers)["days"][0]["tasks"][0]
    client.delete(f"/me/tasks/{main['id']}", headers=headers)

    restored = client.post(
        "/me/tasks/restore",
        json={
            "day_id": day["id"],
            "title": saved["title"],
            "position": saved["position"],
            "subtasks": [
                {
                    "title": s["title"],
                    "position": s["position"],
                    "completed": s["completed"],
                    "notes": s["notes"],
                    "minutes_spent": s["minutes_spent"],
                }
                for s in saved["subtasks"]
            ],
        },
        headers=headers,
    )
    assert restored.status_code == 201

    back = plan(client, headers)["days"][0]["tasks"][0]
    assert back["title"] == saved["title"]
    assert len(back["subtasks"]) == len(saved["subtasks"])
    assert back["subtasks"][0]["completed"] is True
    assert back["subtasks"][0]["minutes_spent"] == 20
    assert back["subtasks"][0]["notes"] == "keep"


def test_a_deleted_day_can_be_restored_in_place(client, register):
    headers = register()
    day = plan(client, headers)["days"][2]
    sub = day["tasks"][0]["subtasks"][0]
    client.put(f"/me/progress/{sub['id']}", json={"completed": True}, headers=headers)
    saved = plan(client, headers)["days"][2]

    client.delete(f"/me/days/{day['id']}", headers=headers)
    assert len(plan(client, headers)["days"]) == 19

    payload = {
        "title": saved["title"],
        "position": saved["position"],
        "tasks": [
            {
                "day_id": day["id"],
                "title": t["title"],
                "position": t["position"],
                "subtasks": [
                    {
                        "title": s["title"],
                        "position": s["position"],
                        "completed": s["completed"],
                        "notes": s["notes"],
                        "minutes_spent": s["minutes_spent"],
                    }
                    for s in t["subtasks"]
                ],
            }
            for t in saved["tasks"]
        ],
    }
    assert client.post("/me/days/restore", json=payload, headers=headers).status_code == 201

    after = plan(client, headers)["days"]
    assert len(after) == 20
    assert after[2]["title"] == saved["title"]
    assert sum(1 for s in leaves(after[2]) if s["completed"]) == 1
    assert [d["position"] for d in after] == list(range(1, 21))


# --- account deletion ---------------------------------------------------


def test_account_summary_counts_what_would_be_lost(client, register):
    headers = register()
    task = leaves(plan(client, headers)["days"][0])[0]
    client.put(f"/me/progress/{task['id']}", json={"completed": True}, headers=headers)
    client.put(f"/me/progress/{task['id']}/notes", json={"notes": "x"}, headers=headers)
    client.put(f"/me/progress/{task['id']}/time", json={"minutes_spent": 10}, headers=headers)

    summary = client.get("/auth/account-summary", headers=headers).json()
    assert summary["days"] == 20
    assert summary["completed_tasks"] == 1
    assert summary["notes"] == 1
    assert summary["minutes_spent"] == 10


def test_delete_account_needs_the_password_and_matching_email(client, register):
    headers = register("del@example.com", "password123")

    assert client.request(
        "DELETE", "/auth/account",
        json={"password": "nope12345", "confirm_email": "del@example.com"}, headers=headers,
    ).status_code == 400
    assert client.request(
        "DELETE", "/auth/account",
        json={"password": "password123", "confirm_email": "other@example.com"}, headers=headers,
    ).status_code == 400
    assert client.get("/me/plan", headers=headers).status_code == 200


def test_delete_account_removes_everything_it_owns(client, register):
    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.models import Day, Task, TaskProgress, User

    headers = register("gone@example.com", "password123")
    task = leaves(plan(client, headers)["days"][0])[0]
    client.put(f"/me/progress/{task['id']}", json={"completed": True}, headers=headers)

    assert client.request(
        "DELETE", "/auth/account",
        json={"password": "password123", "confirm_email": "gone@example.com"}, headers=headers,
    ).status_code == 204

    assert client.get("/me/plan", headers=headers).status_code == 401
    with SessionLocal() as db:
        for model in (User, Day, Task, TaskProgress):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_deleting_one_account_leaves_others_untouched(client, register):
    alice = register("alice@example.com", "password123")
    bob = register("bob@example.com", "password123")

    client.request(
        "DELETE", "/auth/account",
        json={"password": "password123", "confirm_email": "alice@example.com"}, headers=alice,
    )

    assert len(plan(client, bob)["days"]) == 20


# --- moving to an earlier day -------------------------------------------


def test_work_can_be_moved_to_the_previous_day_without_counting_as_carried(client, register):
    headers = register()
    days = plan(client, headers)["days"]
    day2 = days[1]

    result = client.post(
        f"/me/days/{day2['id']}/carry-forward", json={"direction": "previous"}, headers=headers
    ).json()
    assert result["target_day_position"] == 1

    after = plan(client, headers)["days"]
    assert leaves(after[1]) == []
    assert all(t["carried_count"] == 0 for t in leaves(after[0]))

    # Undoing it puts the work back, and must not push the count below zero.
    client.post(
        "/me/tasks/move",
        json={"task_ids": result["moved_task_ids"], "target_day_id": day2["id"]},
        headers=headers,
    )
    assert all(t["carried_count"] == 0 for t in leaves(plan(client, headers)["days"][1]))


def test_the_first_day_has_no_previous_day(client, register):
    headers = register()
    day1 = plan(client, headers)["days"][0]
    response = client.post(
        f"/me/days/{day1['id']}/carry-forward", json={"direction": "previous"}, headers=headers
    )
    assert response.status_code == 400


def test_a_task_without_subtasks_joins_a_same_named_heading_as_a_subtask(client, register):
    headers = register()
    days = plan(client, headers)["days"]
    day1, day2 = days[0], days[1]
    heading = day2["tasks"][0]["title"]
    made = client.post(
        "/me/tasks", json={"day_id": day1["id"], "title": heading}, headers=headers
    ).json()

    client.post(
        f"/me/days/{day1['id']}/carry-forward",
        json={"task_ids": [made["id"]]},
        headers=headers,
    )

    target = plan(client, headers)["days"][1]
    assert [t["title"] for t in target["tasks"]].count(heading) == 1
    group = next(t for t in target["tasks"] if t["title"] == heading)
    assert heading in [s["title"] for s in group["subtasks"]]
