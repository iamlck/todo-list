# Architecture

## Shape

```
Browser ──▶ Vite dev server (5173) ──/api──▶ FastAPI (8000) ──▶ PostgreSQL (5433)
```

The React app never talks to the database. It calls the API, which owns all
validation, authorisation and persistence.

## The data model

A plan is **days → main tasks → subtasks**. `tasks` is a single
self-referencing table: a row with `parent_id` set is a subtask. One table
means completion, notes, time and carry-forward are implemented once instead
of twice, and two levels is enforced at the API rather than by the schema.

Only **leaf** tasks count towards progress — subtasks where they exist, the
main task where it has none. Counting a container and its children would
double-count the same work. Time rolls the other way: a main task reports its
own minutes plus everything beneath it.

The three study areas are ordinary main tasks, not a fixed enum. That is what
lets an uploaded or hand-built plan use the same model as the default one.

## The central design decision

The original spec described a fixed 15-day plan stored in the browser. Two
requirements changed that: multiple users, and a plan each user can edit.

So **task definitions and progress are stored separately**:

- `days` and `tasks` describe *what* the plan contains, and belong to a user.
- `task_progress` records *what has been done* — completion, notes and time —
  keyed by task id.

Because progress is keyed by id rather than by position, renaming, reordering or
carrying a task forward cannot disturb it. Only deleting can — and the UI asks
the server how much work a delete would destroy before confirming
(`GET /me/days/{id}/delete-impact`).

A day's number is derived from its `position` column and never stored twice, so
the two can never disagree. After a delete, positions are compacted back to
`1..n`.

## Tables

| Table            | Key columns                                | Notes |
| ---------------- | ------------------------------------------ | ----- |
| `users`          | `id`, `email` (unique), `password_hash`    | Passwords are bcrypt hashes; the plaintext is never stored |
| `user_settings`  | `user_id`, `start_date`                    | `start_date` is null until chosen |
| `days`           | `id`, `user_id`, `position`, `title`       | Unique `(user_id, position)`, deferrable |
| `tasks`          | `id`, `day_id`, `parent_id`, `title`, `position`, carry-forward columns | `parent_id` null for a main task |
| `task_progress`  | `task_id`, `user_id`, `completed`, `notes`, `minutes_spent`, `timer_started_at` | No row means untouched |

The unique constraint on `(user_id, position)` is **deferrable**: a reorder
rewrites several rows in one transaction and would otherwise collide part-way
through. Postgres checks it at `COMMIT` instead.

## Isolation between users

Every data endpoint depends on `get_current_user`, and every lookup goes through
`get_owned_day` / `get_owned_task` in `backend/app/deps.py`, which filter by
`user_id`. Ownership is re-checked against the object named in the URL and is
never inferred from the request body.

A resource belonging to someone else returns **404, not 403**, so the response
cannot be used to confirm that it exists. `backend/tests/test_auth.py` covers
this.

## Reordering

Reorder endpoints take the **complete ordered list of ids** rather than a
from/to index pair. The client's view of the order wins, applied in one
transaction, so two moves in quick succession cannot interleave into a wrong
result. An incomplete list is rejected with a 400.

## Frontend state

- `AuthContext` — the session. The JWT is kept in `localStorage` purely so a
  reload does not sign you out; all real data is server-side. A 401 from any
  request signs the user out through one shared handler.
- `PlanContext` — the plan, fetched once after login. Ticking a checkbox updates
  the UI immediately and sends the request behind it; if the server rejects it,
  the change is **rolled back** and the error shown, so the page never displays
  progress that was not saved.
- `lib/progress.js` — every percentage and status calculation, as pure
  functions, shared by the dashboard, day view and editor so they cannot
  disagree.

## Notes and time

`task_progress` holds notes and `minutes_spent` alongside completion, so a task
can carry notes and recorded time while still unticked, and all of it follows
the task when it is renamed, reordered or carried forward.

Time is recorded two ways into one figure. A manual entry sets or adjusts
`minutes_spent` directly. A timer sets `timer_started_at`; stopping it folds the
elapsed minutes into `minutes_spent` and clears the stamp. **Only one timer runs
at a time** — starting one stops any other, and completing a task stops its own
— because two running timers would count the same stretch of work twice. The
elapsed figure is computed from the stored timestamp, so it stays correct
across reloads and is never lost to a closed tab.

## Carry forward

`POST /me/days/{id}/carry-forward` **moves** chosen unfinished tasks to another
day by reassigning their `day_id`. The request names them in `task_ids`;
omitting it falls back to everything unfinished. Completed tasks are filtered
out server-side even if named, so finished work is never relocated.

Where they land is decided in one place, in precedence order: an explicit
`target_day_id` wins; otherwise `direction` picks the neighbouring day, `next`
(the default) or `previous`. Work slips backwards as often as forwards — a day
finished early can absorb tomorrow's list — so the same endpoint serves both
rather than a second one being added for it.

Two details make the result read well rather than merely correct:

- **Merging.** A main task whose name already exists on the target day has its
  unfinished subtasks moved into that heading, and the emptied heading is
  removed — so a day never ends up with two "Kubernetes" sections.
- **Re-homing.** A subtask moved on its own is placed under a same-named main
  task on the target, created if absent, rather than being orphaned.

Moving rather than copying matters: the work is listed once, totals stay
truthful, and the source day can actually reach "Completed". Because task ids do
not change, notes and recorded time travel with them. Positions in the source day
are then compacted so no gaps remain.

Each moved task records `carried_count`, `last_carried_from`, `last_carried_at`
and `original_day_position`, which is what the ↷ badge in the UI reads. Undoing a
carry-forward decrements the count again. (`last_carried_at` is stored but not
returned by the API — nothing displays it yet.)

## Password reset

`password_reset_tokens` stores a **SHA-256 hash** of each token, never the token
itself, so a database dump yields no working links. A fast hash is appropriate
here because the token is 256 bits of randomness, unlike a human-chosen password
which needs bcrypt.

Tokens expire after 30 minutes and are single-use; requesting a new one marks
any outstanding tokens used. `POST /auth/forgot-password` always returns the
same response whether or not the email is registered, so it cannot be used to
enumerate accounts.

With no mail server, the link is logged by the API. Replacing the `log.warning`
in `app/routers/auth.py` with an SMTP send is the only change needed for real
email.

## Undo

Undo is held in the running page (`UndoContext`), holding one pending action at
a time. Each undoable action captures what it needs *before* acting:

- **Carry-forward** returns `moved_task_ids`, and undo posts them back to the
  original day. The same rows move, so completion and notes are inherently
  preserved — nothing is copied or recreated.
- **Deleting a task or a day** snapshots it client-side first, since the rows
  are really gone afterwards. Restore recreates them with their completion and
  notes, and puts a day back at its original position rather than appending it.
  Restored items get **new ids**: this is a faithful restore, not a resurrection
  of the original rows.

Deleting several tasks at once is a **client-side loop** over
`DELETE /me/tasks/{id}`, not a bulk endpoint. Each call returns its
`deleted_log_ids`, which the page collects so a single undo restores the whole
set — parents before subtasks, since a subtask needs its parent to exist. A
batch endpoint would be faster over the wire but would need its own partial-failure
semantics; looping leaves each delete atomic and independently undoable.

Keeping undo in memory is deliberate. A durable recycle bin would need deleted
rows, a retention policy and a purge job; the value here is catching a misclick,
which memory covers. The UI says as much rather than implying more.

## Deleting an account

`DELETE /auth/account` removes the user row, and every foreign key cascades
from it, so no days, tasks, progress, notes or reset tokens survive. Two
guards precede it — the current password, and typing the account's own email —
because there is no undo for this one. A test asserts that the tables are empty
afterwards and that other accounts are untouched.

## The time report

`/time` is derived entirely from the plan already in memory — no extra request
and no server-side aggregation — so its figures can never disagree with the day
views.

Two details worth knowing. **Totals sum main tasks only**, because a main task
already includes its subtasks' minutes; adding both would double-count.
And the **average is over days actually worked**, not every day in the plan: a
plan with sixteen untouched days ahead would otherwise report an average that
describes nothing.

The charts show one measure, minutes, so they use a **single hue** — colour
carries no meaning, length does, and no categorical palette is involved. Each
chart has a table view beside it, and bars carry their values as text rather
than relying on the mark alone.

## Export

`frontend/src/lib/export.js` builds CSV and JSON **entirely in the browser**.
The page already holds the whole plan, so a server round-trip would fetch data
it has and add an endpoint to maintain; there is deliberately no export route.

The CSV is one row per unit of work — each subtask, or a main task that has none
— which is exactly the set progress is counted on, so a spreadsheet of it agrees
with the dashboard. Two details are easy to mistake for bugs:

- A **UTF-8 BOM** is prepended, because Excel otherwise reads accented characters
  as mojibake.
- Values beginning `=`, `+`, `-` or `@` are prefixed with an apostrophe. That is
  **formula-injection defence**: a task titled `=cmd|...` would otherwise execute
  as a formula when the file is opened. Numeric values are left alone.

JSON is the raw day/task tree plus `exported_at` and `start_date`, for anything
that wants the structure rather than a flat table.

## Task status

Three states from two columns: `completed`, and `started_at` on
`task_progress`. Not started is neither; in progress is `started_at` with no
completion; completed is `completed`.

Start is explicit — a button, not an inference from activity — but two paths
set it implicitly, because the alternative is a state that contradicts itself:
starting a timer, and completing a task that was never marked started. Clearing
Start also unticks the task and stops its timer, so the three states can never
disagree with the data behind them.

A parent's status is derived, never stored: in progress when any child is
started or done, completed when all are. Storing it would mean two sources of
truth to keep in step.

## The deletion log

`deleted_tasks` records what was removed: title, day position and title, parent
title, whether it was completed, minutes recorded, subtask count, and whether
it went on its own or with its day.

Every field is **copied, not referenced**. A foreign key to the task would
cascade away with it, and one to the day would break when the day is deleted
too — leaving a log that says nothing. Copying is what makes the record
survive.

It is a log rather than a recycle bin, so nothing is restorable from it.
Session undo still works, and passes the entry ids to the restore endpoint so
they are marked `restored_at` instead of leaving the history asserting
something untrue.

## Administration

A single `users.is_admin` flag, granted only by `scripts/make_admin.py`. No
self-service promotion exists, so an ordinary account cannot escalate through
the API however it is called.

The two roles are separated in the client: `UserOnly` sends an administrator
to `/admin`, `AdminOnly` sends everyone else to the dashboard, and the
navigation shows one set of links or the other. The API stays permissive about
an admin owning a plan, deliberately — that way promoting an account only
*hides* its tracker, and demoting it brings the data back rather than
stranding it.

`get_current_admin` raises **404, not 403**, so the admin area is invisible to
accounts that cannot use it — a 403 would confirm the routes exist.

The user list builds its per-account figures from **scalar subqueries** rather
than joins. Joining days, tasks and progress in one statement would multiply
the rows and inflate every count; a test asserts the figures stay correct for
a user with real data.

Two invariants are enforced server-side: an administrator cannot withdraw
their own rights (which would lock them out mid-session), and the last
administrator cannot be withdrawn (which would leave the installation with no
way in). Deleting another account needs the administrator's own password plus
the target's email, and cascades through every table the user owns.

## Deliberate omissions

Deferred, with room left in the schema and API: per-task resource links, a full
reset, deeper task nesting, restoring from the deletion log, undo that survives a
reload, and a server-side bulk-delete endpoint.

(Export shipped — see *Export* above. Import shipped earlier, as
`POST /me/plan/setup` with `mode: "import"`.)
