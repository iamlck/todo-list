"""Task status (not started / in progress / completed) and the deletion log."""


def plan(client, headers):
    return client.get("/me/plan", headers=headers).json()


def first_main(client, headers):
    return plan(client, headers)["days"][0]["tasks"][0]


# --- status -------------------------------------------------------------


def test_a_task_starts_out_not_started(client, register):
    headers = register()
    main = first_main(client, headers)
    assert main["status"] == "not-started"
    assert all(s["status"] == "not-started" for s in main["subtasks"])


def test_pressing_start_marks_a_task_in_progress(client, register):
    headers = register()
    sub = first_main(client, headers)["subtasks"][0]

    response = client.put(f"/me/progress/{sub['id']}/start", json={"started": True}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "in-progress"

    after = first_main(client, headers)
    assert after["subtasks"][0]["status"] == "in-progress"
    assert after["subtasks"][0]["started_at"] is not None
    # A main task is underway as soon as one of its subtasks is.
    assert after["status"] == "in-progress"


def test_start_can_be_cleared_again(client, register):
    headers = register()
    sub = first_main(client, headers)["subtasks"][0]
    client.put(f"/me/progress/{sub['id']}/start", json={"started": True}, headers=headers)

    client.put(f"/me/progress/{sub['id']}/start", json={"started": False}, headers=headers)
    assert first_main(client, headers)["subtasks"][0]["status"] == "not-started"


def test_completing_a_task_implies_it_was_started(client, register):
    headers = register()
    sub = first_main(client, headers)["subtasks"][0]

    client.put(f"/me/progress/{sub['id']}", json={"completed": True}, headers=headers)

    after = first_main(client, headers)["subtasks"][0]
    assert after["status"] == "completed"
    # Never "completed but never started".
    assert after["started_at"] is not None


def test_starting_a_timer_marks_the_task_started(client, register):
    headers = register()
    sub = first_main(client, headers)["subtasks"][0]

    client.post(f"/me/progress/{sub['id']}/timer/start", headers=headers)

    assert first_main(client, headers)["subtasks"][0]["status"] == "in-progress"


def test_a_main_task_completes_only_when_all_subtasks_do(client, register):
    headers = register()
    main = first_main(client, headers)

    for sub in main["subtasks"][:-1]:
        client.put(f"/me/progress/{sub['id']}", json={"completed": True}, headers=headers)
    assert first_main(client, headers)["status"] == "in-progress"

    client.put(f"/me/progress/{main['subtasks'][-1]['id']}", json={"completed": True}, headers=headers)
    assert first_main(client, headers)["status"] == "completed"


# --- deletion history ---------------------------------------------------


def test_deleting_a_task_is_recorded(client, register):
    headers = register()
    main = first_main(client, headers)
    sub = main["subtasks"][0]
    client.put(f"/me/progress/{sub['id']}", json={"completed": True}, headers=headers)
    client.put(f"/me/progress/{sub['id']}/time", json={"minutes_spent": 30}, headers=headers)

    result = client.delete(f"/me/tasks/{main['id']}", headers=headers).json()
    assert len(result["deleted_log_ids"]) == 1

    log = client.get("/me/deleted-tasks", headers=headers).json()
    assert len(log) == 1
    entry = log[0]
    assert entry["title"] == main["title"]
    assert entry["day_position"] == 1
    assert entry["day_title"] == "Foundations"
    assert entry["subtask_count"] == len(main["subtasks"])
    assert entry["minutes_spent"] == 30
    assert entry["reason"] == "task"
    assert entry["restored_at"] is None


def test_a_deleted_subtask_records_its_parent(client, register):
    headers = register()
    main = first_main(client, headers)
    sub = main["subtasks"][0]

    client.delete(f"/me/tasks/{sub['id']}", headers=headers)

    entry = client.get("/me/deleted-tasks", headers=headers).json()[0]
    assert entry["title"] == sub["title"]
    assert entry["parent_title"] == main["title"]


def test_deleting_a_day_records_each_main_task(client, register):
    headers = register()
    day = plan(client, headers)["days"][0]

    result = client.delete(f"/me/days/{day['id']}", headers=headers).json()
    assert len(result["deleted_log_ids"]) == len(day["tasks"])

    log = client.get("/me/deleted-tasks", headers=headers).json()
    assert {e["title"] for e in log} == {t["title"] for t in day["tasks"]}
    assert all(e["reason"] == "day" for e in log)
    # Recorded where it was, even though that day no longer exists.
    assert all(e["day_position"] == 1 for e in log)


def test_undoing_a_delete_marks_the_entry_restored(client, register):
    headers = register()
    day = plan(client, headers)["days"][0]
    main = day["tasks"][0]

    result = client.delete(f"/me/tasks/{main['id']}", headers=headers).json()
    client.post(
        "/me/tasks/restore",
        json={
            "deleted_log_ids": result["deleted_log_ids"],
            "day_id": day["id"],
            "title": main["title"],
            "position": main["position"],
            "subtasks": [{"title": s["title"]} for s in main["subtasks"]],
        },
        headers=headers,
    )

    entry = client.get("/me/deleted-tasks", headers=headers).json()[0]
    # The history no longer claims it is gone.
    assert entry["restored_at"] is not None

    unrestored = client.get(
        "/me/deleted-tasks", params={"include_restored": False}, headers=headers
    ).json()
    assert unrestored == []


def test_history_is_private_to_its_owner(client, register):
    alice = register("alice@example.com")
    bob = register("bob@example.com")

    main = first_main(client, alice)
    client.delete(f"/me/tasks/{main['id']}", headers=alice)

    assert len(client.get("/me/deleted-tasks", headers=alice).json()) == 1
    assert client.get("/me/deleted-tasks", headers=bob).json() == []


def test_history_is_newest_first(client, register):
    headers = register()
    day = plan(client, headers)["days"][0]

    client.delete(f"/me/tasks/{day['tasks'][0]['id']}", headers=headers)
    client.delete(f"/me/tasks/{day['tasks'][1]['id']}", headers=headers)

    log = client.get("/me/deleted-tasks", headers=headers).json()
    assert [e["title"] for e in log] == [day["tasks"][1]["title"], day["tasks"][0]["title"]]
