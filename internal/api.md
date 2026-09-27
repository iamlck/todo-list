# API reference

Base URL in development: `http://localhost:8000` (the frontend reaches it as
`/api`, proxied by Vite). Interactive docs: `/docs`.

All `/me/*` endpoints require `Authorization: Bearer <token>`. Without a valid
token they return **401**. A resource owned by a different user returns **404**,
never 403.

## Auth

| Method | Path           | Body                     | Returns |
| ------ | -------------- | ------------------------ | ------- |
| POST   | `/auth/signup` | `{email, password}`      | 201 · `{access_token, token_type, user}` — also creates this user's copy of the default plan |
| POST   | `/auth/login`  | `{email, password}`      | 200 · same shape |
| GET    | `/auth/me`     | —                        | 200 · `{id, email}` |
| POST   | `/auth/forgot-password` | `{email}`       | 202 · always the same reply, whether or not the email is registered. The reset link is written to the API log |
| POST   | `/auth/reset-password`  | `{token, password}` | 200 · signs the user in. The token is single-use and expires after 30 minutes |
| POST   | `/auth/change-password` | `{current_password, new_password}` | 204 · requires a valid session and the current password |
| GET    | `/auth/account-summary` | —                       | `{email, days, topics, completed_topics, notes}` — what a deletion would destroy |
| DELETE | `/auth/account`         | `{password, confirm_email}` | 204 · **permanent**. Requires the current password and the account's own email. Cascades to the plan, progress, notes and reset tokens |

Passwords must be at least 8 characters. A duplicate email returns 409. A bad
login returns 401 with the same message whether the email exists or not.

## Plan

A plan is days -> main tasks -> subtasks. A task with `parent_id` set is a
subtask; two levels is the whole model.

| Method | Path                            | Body                          | Returns |
| ------ | ------------------------------- | ----------------------------- | ------- |
| GET    | `/me/plan`                      | —                             | `{start_date, onboarded, days[]}` — each task carries `status` (`not-started`/`in-progress`/`completed`), `completed`, `started_at`, `notes`, `minutes_spent`, `timer_started_at`, carry-forward history and nested `subtasks` |
| POST   | `/me/plan/setup`                | `{mode, day_count?, days?}`   | 201 · creates the plan. `mode` is `default` (the 20-day plan), `blank` (needs `day_count`) or `import` (needs `days`). 409 once a plan exists |
| POST   | `/me/days`                      | `{title, position?}`          | 201 · the new day, appended when `position` is omitted |
| PATCH  | `/me/days/{id}`                 | `{title}`                     | the updated day |
| DELETE | `/me/days/{id}`                 | —                             | `{deleted_log_ids}` · cascades to its tasks and progress; remaining days are renumbered, and each main task is written to the deletion log |
| GET    | `/me/days/{id}/delete-impact`   | —                             | `{tasks, completed_tasks, minutes_spent}` — for the confirmation prompt |
| PUT    | `/me/days/reorder`              | `{ids}`                       | 204 · send every day id exactly once |
| POST   | `/me/tasks`                     | `{day_id, parent_id?, title}` | 201 · omit `parent_id` for a main task. 400 if the parent is itself a subtask |
| PATCH  | `/me/tasks/{id}`                | `{title}`                     | the updated task; progress is unaffected |
| DELETE | `/me/tasks/{id}`                | —                             | `{deleted_log_ids}` · cascades to its subtasks and writes a deletion-log entry |
| PUT    | `/me/tasks/reorder`             | `{day_id, parent_id, ids}`    | 204 · send every id at that level exactly once |

### History

| Method | Path                 | Query                              | Returns |
| ------ | -------------------- | ---------------------------------- | ------- |
| GET    | `/me/deleted-tasks`  | `limit` (≤500), `include_restored` | deleted tasks, newest first, each with title, day, parent, counts, time and `restored_at` |

### Carrying work forward and undo

| Method | Path                          | Body                          | Returns |
| ------ | ----------------------------- | ----------------------------- | ------- |
| POST   | `/me/days/{id}/carry-forward` | `{task_ids?, target_day_id?}` | `{moved, target_day_position, moved_task_ids}` — **moves** the chosen unfinished tasks. Omit `task_ids` to move everything unfinished; `target_day_id` defaults to the next day. Completed tasks are skipped even if named. 400 on an empty selection, a task from another day, the last day, or the same target day |
| POST   | `/me/tasks/move`              | `{task_ids, target_day_id}`   | 204 · moves specific tasks. Undoes a carry-forward, decrementing the history entry |
| POST   | `/me/tasks/restore`           | `{deleted_log_ids?, day_id, parent_id?, title, position?, completed?, notes?, minutes_spent?, subtasks[]}` | 201 · recreates a deleted task with its progress. It gets a new id; any `deleted_log_ids` are marked restored |
| POST   | `/me/days/restore`            | `{title, position?, tasks[]}` | 201 · recreates a deleted day and everything on it |

## Progress, time and settings

| Method | Path                              | Body                            | Returns |
| ------ | --------------------------------- | ------------------------------- | ------- |
| PUT    | `/me/progress/{task_id}`          | `{completed}`                   | ticking a main task ticks its subtasks, and stops any running timer |
| PUT    | `/me/progress/{task_id}/start`    | `{started}`                     | marks the task in progress, or clears it back to not started (which also unticks it and stops its timer) |
| PUT    | `/me/progress/{task_id}/notes`    | `{notes}`                       | free text up to 5000 characters |
| PUT    | `/me/progress/{task_id}/time`     | `{minutes_spent}` or `{add_minutes}` | sets or adjusts recorded time; never drops below zero. 400 if neither is sent |
| POST   | `/me/progress/{task_id}/timer/start` | —                            | starts timing, stopping any timer running elsewhere |
| POST   | `/me/progress/{task_id}/timer/stop`  | —                            | folds the elapsed minutes into the total |
| PUT    | `/me/settings`                    | `{start_date}`                  | `YYYY-MM-DD`, or `null` to clear. Only moves which day counts as "today" |

## Administration

Every route requires an administrator. For an ordinary account they return
**404**, so the area is invisible rather than merely forbidden.

| Method | Path                  | Body / query                   | Returns |
| ------ | --------------------- | ------------------------------ | ------- |
| GET    | `/admin/users`        | `q` (email filter), `limit` (≤500) | accounts newest first, each with `is_admin`, `created_at`, `onboarded`, `start_date`, `days`, `tasks`, `completed_tasks`, `minutes_spent`, `last_activity`. Counts only — never note contents |
| GET    | `/admin/users/{id}`   | —                              | the same shape for one account |
| PATCH  | `/admin/users/{id}`   | `{is_admin}`                   | grants or withdraws rights. 400 on withdrawing your own, or the last administrator's |
| DELETE | `/admin/users/{id}`   | `{password, confirm_email}`    | 204 · **permanent**. Needs the *administrator's* password and the *target's* email. 400 when deleting yourself — use `/auth/account` |

`/auth/me` and the login response include `is_admin`.

## Meta

`GET /health` → `{"status": "ok"}`, unauthenticated.

Each topic in `GET /me/plan` carries a `notes` string, empty when none have been
written.

## Example

```bash
TOKEN=$(curl -s -X POST localhost:8000/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"password123"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -s localhost:8000/me/plan -H "Authorization: Bearer $TOKEN"
```
