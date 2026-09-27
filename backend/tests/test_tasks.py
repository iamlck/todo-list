"""Editing the plan, progress, notes and time."""


def plan(client, headers):
    return client.get("/me/plan", headers=headers).json()


def first_subtask(client, headers, day_index=0):
    return plan(client, headers)["days"][day_index]["tasks"][0]["subtasks"][0]


def test_progress_is_saved_and_read_back(client, register):
    headers = register()
    task = first_subtask(client, headers)

    client.put(f"/me/progress/{task['id']}", json={"completed": True}, headers=headers)
    assert first_subtask(client, headers)["completed"] is True

    client.put(f"/me/progress/{task['id']}", json={"completed": False}, headers=headers)
    assert first_subtask(client, headers)["completed"] is False


def test_a_main_task_is_complete_when_its_subtasks_are(client, register):
    headers = register()
    main = plan(client, headers)["days"][0]["tasks"][0]
    assert main["completed"] is False

    for sub in main["subtasks"]:
        client.put(f"/me/progress/{sub['id']}", json={"completed": True}, headers=headers)

    assert plan(client, headers)["days"][0]["tasks"][0]["completed"] is True


def test_ticking_a_main_task_ticks_its_subtasks(client, register):
    headers = register()
    main = plan(client, headers)["days"][0]["tasks"][0]

    client.put(f"/me/progress/{main['id']}", json={"completed": True}, headers=headers)

    after = plan(client, headers)["days"][0]["tasks"][0]
    assert after["completed"] is True
    assert all(s["completed"] for s in after["subtasks"])


def test_notes_survive_renaming_and_completion(client, register):
    headers = register()
    task = first_subtask(client, headers)

    client.put(f"/me/progress/{task['id']}/notes", json={"notes": "read the docs"}, headers=headers)
    client.patch(f"/me/tasks/{task['id']}", json={"title": "Renamed"}, headers=headers)
    client.put(f"/me/progress/{task['id']}", json={"completed": True}, headers=headers)

    after = first_subtask(client, headers)
    assert after["title"] == "Renamed"
    assert after["notes"] == "read the docs"
    assert after["completed"] is True


# --- time ---------------------------------------------------------------


def test_time_can_be_set_and_added_to(client, register):
    headers = register()
    task = first_subtask(client, headers)

    client.put(f"/me/progress/{task['id']}/time", json={"minutes_spent": 30}, headers=headers)
    assert first_subtask(client, headers)["minutes_spent"] == 30

    client.put(f"/me/progress/{task['id']}/time", json={"add_minutes": 15}, headers=headers)
    assert first_subtask(client, headers)["minutes_spent"] == 45

    # An adjustment can never push the total below zero.
    client.put(f"/me/progress/{task['id']}/time", json={"add_minutes": -999}, headers=headers)
    assert first_subtask(client, headers)["minutes_spent"] == 0


def test_time_rolls_up_from_subtasks_to_the_main_task(client, register):
    headers = register()
    main = plan(client, headers)["days"][0]["tasks"][0]

    for minutes, sub in zip((20, 25), main["subtasks"]):
        client.put(f"/me/progress/{sub['id']}/time", json={"minutes_spent": minutes}, headers=headers)

    assert plan(client, headers)["days"][0]["tasks"][0]["minutes_spent"] == 45


def test_time_endpoint_needs_a_value(client, register):
    headers = register()
    task = first_subtask(client, headers)
    assert client.put(f"/me/progress/{task['id']}/time", json={}, headers=headers).status_code == 400


def test_timer_records_elapsed_time_and_only_one_runs_at_once(client, register):
    from datetime import datetime, timedelta, timezone

    from app.db import SessionLocal
    from app.models import TaskProgress

    headers = register()
    main = plan(client, headers)["days"][0]["tasks"][0]
    first, second = main["subtasks"][0], main["subtasks"][1]

    client.post(f"/me/progress/{first['id']}/timer/start", headers=headers)
    assert first_subtask(client, headers)["timer_started_at"] is not None

    # Backdate the start so there is measurable elapsed time.
    with SessionLocal() as db:
        row = db.get(TaskProgress, first["id"])
        row.timer_started_at = datetime.now(timezone.utc) - timedelta(minutes=25)
        db.commit()

    # Starting a second timer stops the first, so time is never double-counted.
    client.post(f"/me/progress/{second['id']}/timer/start", headers=headers)

    after = plan(client, headers)["days"][0]["tasks"][0]["subtasks"]
    assert after[0]["timer_started_at"] is None
    assert after[0]["minutes_spent"] == 25
    assert after[1]["timer_started_at"] is not None


def test_completing_a_task_stops_its_timer(client, register):
    headers = register()
    task = first_subtask(client, headers)

    client.post(f"/me/progress/{task['id']}/timer/start", headers=headers)
    client.put(f"/me/progress/{task['id']}", json={"completed": True}, headers=headers)

    assert first_subtask(client, headers)["timer_started_at"] is None


# --- editing ------------------------------------------------------------


def test_adding_a_main_task_and_a_subtask(client, register):
    headers = register()
    day = plan(client, headers)["days"][0]

    main = client.post(
        "/me/tasks", json={"day_id": day["id"], "title": "Extra reading"}, headers=headers
    ).json()
    client.post(
        "/me/tasks",
        json={"day_id": day["id"], "parent_id": main["id"], "title": "Chapter 4"},
        headers=headers,
    )

    after = plan(client, headers)["days"][0]["tasks"]
    added = next(t for t in after if t["title"] == "Extra reading")
    assert [s["title"] for s in added["subtasks"]] == ["Chapter 4"]


def test_subtasks_cannot_be_nested_further(client, register):
    headers = register()
    day = plan(client, headers)["days"][0]
    sub = day["tasks"][0]["subtasks"][0]

    response = client.post(
        "/me/tasks",
        json={"day_id": day["id"], "parent_id": sub["id"], "title": "Too deep"},
        headers=headers,
    )
    assert response.status_code == 400


def test_deleting_a_main_task_removes_its_subtasks(client, register):
    headers = register()
    day = plan(client, headers)["days"][0]
    main = day["tasks"][0]

    client.delete(f"/me/tasks/{main['id']}", headers=headers)

    after = plan(client, headers)["days"][0]["tasks"]
    assert all(t["id"] != main["id"] for t in after)
    assert len(after) == len(day["tasks"]) - 1


def test_reordering_subtasks_keeps_their_progress(client, register):
    headers = register()
    day = plan(client, headers)["days"][0]
    main = day["tasks"][0]
    client.put(f"/me/progress/{main['subtasks'][0]['id']}", json={"completed": True}, headers=headers)

    reversed_ids = [s["id"] for s in reversed(main["subtasks"])]
    response = client.put(
        "/me/tasks/reorder",
        json={"day_id": day["id"], "parent_id": main["id"], "ids": reversed_ids},
        headers=headers,
    )
    assert response.status_code == 204

    after = plan(client, headers)["days"][0]["tasks"][0]["subtasks"]
    assert [s["id"] for s in after] == reversed_ids
    assert next(s for s in after if s["id"] == main["subtasks"][0]["id"])["completed"] is True


def test_adding_and_deleting_days_renumbers_positions(client, register):
    headers = register()

    assert client.post("/me/days", json={"title": "Day 21"}, headers=headers).status_code == 201
    days = plan(client, headers)["days"]
    assert len(days) == 21

    client.delete(f"/me/days/{days[1]['id']}", headers=headers)
    after = plan(client, headers)["days"]
    assert [d["position"] for d in after] == list(range(1, 21))


def test_delete_impact_reports_tasks_progress_and_time(client, register):
    headers = register()
    day = plan(client, headers)["days"][0]
    sub = day["tasks"][0]["subtasks"][0]
    client.put(f"/me/progress/{sub['id']}", json={"completed": True}, headers=headers)
    client.put(f"/me/progress/{sub['id']}/time", json={"minutes_spent": 40}, headers=headers)

    impact = client.get(f"/me/days/{day['id']}/delete-impact", headers=headers).json()
    assert impact["completed_tasks"] == 1
    assert impact["minutes_spent"] == 40
    assert impact["tasks"] > 0


def test_start_date_can_change_without_touching_progress(client, register):
    headers = register()
    task = first_subtask(client, headers)
    client.put(f"/me/progress/{task['id']}", json={"completed": True}, headers=headers)

    client.put("/me/settings", json={"start_date": "2026-09-01"}, headers=headers)

    result = plan(client, headers)
    assert result["start_date"] == "2026-09-01"
    assert first_subtask(client, headers)["completed"] is True
