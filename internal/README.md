# Learning Tracker

A study tracker for a multi-day learning plan. A plan is **days → main tasks →
subtasks**, and every account owns its own, editable throughout.

New accounts choose how to start: the built-in **20-day plan** covering AWS
CloudOps, Kubernetes and GenAI; a chosen number of empty days; or a CSV upload
of a plan you already have. Every task records **time spent** and, when it slips,
its **carry-forward history**.

This is a personal study tracker. It does not guarantee any exam result.

## Layout

| Path        | Contents                                              |
| ----------- | ----------------------------------------------------- |
| `backend/`  | FastAPI application, its config, and tests            |
| `frontend/` | React + Vite application                              |
| `internal/` | Documentation (this folder holds the Markdown only)   |
| `docker-compose.yml` | The PostgreSQL and API containers            |

Further reading: **[guide.md](guide.md) — the complete guide to using the app,
written for a non-technical reader**; [architecture.md](architecture.md) for how
it fits together; [api.md](api.md) for the endpoints; [spec.md](spec.md) for the
original requirements.

## Prerequisites

- Docker, with Compose. Commands below use `docker-compose` (hyphenated);
  if your install provides the newer plugin instead, use `docker compose`.
  On macOS with Colima, run `colima start` first.
- No local PostgreSQL install needed
- Python 3.11+
- Node 18+

## Setup

The backend can run either in Docker or directly on your machine. Docker is the
fewest steps; running it locally gives faster restarts and easier debugging.

### Option A — database and backend in Docker (recommended)

```bash
cp backend/.env.example backend/.env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET
docker-compose up -d --build
```

That starts PostgreSQL and the API together. Compose overrides `DATABASE_URL`
so the container reaches the database as `db:5432`; the value in your `.env` is
the one used when running the backend outside Docker. Source is mounted into
the container with `--reload`, so edits apply without a rebuild.

```bash
docker-compose logs -f api     # follow the API logs
docker-compose down            # stop (data survives in the volume)
```

Rebuild after changing `requirements.txt`: `docker-compose up -d --build`.

### Option B — database in Docker, backend locally

```bash
docker-compose up -d db
cd backend
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn app.main:app --reload --port 8000
```

Only one of the two may hold port 8000 at a time. Stop the container first with
`docker-compose stop api`.

### Frontend (both options)

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173> and create an account.

Tables are created automatically at startup. Interactive API docs:
<http://localhost:8000/docs>. The dev server proxies `/api` to the backend, so
the browser makes no cross-origin requests in development.

## Tests

```bash
cd backend && ./.venv/bin/pytest
```

Or inside the container: `docker-compose exec api pytest`.

They run against a separate `tracker_test` database, created automatically, so
your own data is never touched. The database container must be running.

## Setting up a plan

The first screen after signing up offers three starting points:

1. **The default plan** — 20 days of AWS CloudOps, Kubernetes and GenAI, from
   foundations through a capstone to the exam.
2. **A number of empty days** — pick how many and fill them in as you go.
3. **A CSV upload** — for a plan you already have.

For the upload, *Download template* gives a worked example. The columns are
`day, day_title, main_task, subtask`, one row per subtask, repeating the day and
main task across rows. Excel and Google Sheets both export CSV. The file is
parsed in your browser and previewed — days, tasks and subtask counts — before
anything is saved.

Whichever you choose, everything stays editable under **Edit plan**.

## Tasks, subtasks and time

Tasks can be added straight from the day you are looking at — **+ Add a
subtask** under each main task, **+ Add a main task** at the foot of the day —
so work that comes up mid-session does not need a trip to the editor. The
editor remains the place to rename, reorder, delete and reshape.

A day holds main tasks; each main task holds subtasks. Ticking every subtask
completes its main task, and ticking a main task ticks everything under it.
Progress counts the leaves, so work is never double-counted.

**Time spent** — each task has a **▶ Start** timer and a figure you can click to
type minutes directly. Starting a timer stops any other, so the same stretch of
time is never counted twice, and completing a task stops its timer. Time rolls
up from subtasks to their main task and on to the day and the dashboard.

**Where to see it** — the time figure appears beside each task, on its main
task heading, under the day's progress bar, and as a total on the dashboard.
The **Time** page pulls it together: total, days worked, average per day
worked, busiest day, a bar per day, totals by subject (main tasks of the same
name added up across the plan), and your longest individual tasks. Each chart
has a table view, and the per-day chart links straight to that day.

**Notes** — every task has a *Notes* toggle. Text saves automatically a moment
after you stop typing, and a task can carry notes while still unticked.

## Task status

Every task is **Not started**, **In progress** or **Completed**, shown as a pill
beside it and summarised on the dashboard.

Press **Start** to mark a task underway; press **Not started** to clear it
again. Two things set it for you, because the alternative would be a lie:
starting a timer marks the task started, and completing one records that it was
started if you never pressed the button.

A main task follows its subtasks — in progress as soon as any of them is
started or finished, completed only when all of them are. A day is in progress
once anything on it has been started.

## Carrying work forward

When a day runs out, the day view offers *Carry forward…*, which lists that
day's unfinished tasks. Everything starts ticked, so untick whatever should
stay, choose the destination day (the next one by default), and confirm.

Selected tasks **move** rather than being copied, so nothing is listed twice and
the old day can genuinely be completed. Notes and recorded time travel with
them, and carried work merges into a main task of the same name on the target
day rather than creating a second heading.

Each task keeps its **carry-forward history** — a ↷ badge showing how many times
it has slipped and which day it last came from. Undo is offered afterwards, and
reverses the history entry too.

## Undo

Carrying work forward, deleting a topic and deleting a day each offer **Undo**
in a bar at the top of the page. Undo restores completion and notes as well as
the item itself; a restored day goes back in its original slot rather than at
the end.

Undo lives in the running page, so it is offered until you navigate away or
take another undoable action. It is a safety net for a misclick, not a recycle
bin — nothing is recoverable after a reload.

Two things it does not cover. Ticking a box is already reversed by unticking
it. And **deleting your account cannot be undone at all.**

## Deleted tasks

**History** lists every task you have deleted, newest first, with the day it
was on, its parent task, how many subtasks went with it, whether it was
completed, and how much time had been recorded. Tasks removed as part of
deleting a whole day are marked as such.

This is a history log, not a recycle bin — it records what happened and keeps
nothing to restore from. To bring something back, use **Undo** straight after
deleting, which also marks the history entry as restored so it stops claiming
the task is gone. Otherwise, add it again in the editor.

## Administration

**The two roles are separate.** A learner account has the tracker — dashboard,
days, editor, history — and no admin area. An administrator account has the
Users page and no plan of its own: administering accounts and following a study
plan are different jobs, so one account does not do both. Keep a learner
account for your own study and a separate account for administration.

An administrator sees a **Users** link in the top bar and a `/admin` page
listing every account: when it was created, whether a plan is set up, how many
days and tasks it holds, how many are done, time recorded, and last activity.
From there they can grant or withdraw admin rights, and delete an account.

Administrators see **counts and totals only** — never the contents of anyone's
notes. Knowing how much work an account holds is enough to administer it.

There is deliberately no way to promote yourself through the UI, so the first
administrator is made from the command line:

```bash
docker-compose exec api python scripts/make_admin.py you@example.com
docker-compose exec api python scripts/make_admin.py them@example.com --remove
```

Guards worth knowing: you cannot withdraw your own rights, the last
administrator cannot be withdrawn, and deleting someone else's account asks for
**your** password plus **their** email. Deleting your own account stays on the
Account page. None of it can be undone.

For everyone else the admin routes return **404, not 403** — the area does not
announce itself to accounts that cannot use it.

Promoting an account hides its tracker but **does not delete anything**: its
plan and progress stay in the database and come back if the account is demoted
again.

## Deleting your account

Under **Account**, *Delete account* removes the account and everything on it,
permanently. It shows what will be lost first and asks for both your password
and your own email address. There is no undo and no recycle bin, so take a
backup first if the data might matter:

```bash
docker exec learning-tracker-db pg_dump -U tracker tracker > backup.sql
```

Other accounts are unaffected.

## Forgotten password

Use **Forgot your password?** on the sign-in screen. Because there is no mail
server, the reset link is written to the API log instead of emailed:

```bash
docker-compose logs --tail=20 api
```

The link is valid for 30 minutes and works once; requesting a new one
invalidates the previous. To send real email instead, replace the `log.warning`
call in `backend/app/routers/auth.py` with an SMTP send.

If you would rather not use the browser at all, set a password directly:

```bash
docker-compose exec api python scripts/set_password.py you@example.com
# or, with the backend running locally:
cd backend && ./.venv/bin/python scripts/set_password.py you@example.com
```

Signed in, you can change your password under **Account**. Either way your plan
and progress are untouched.

## How your progress is stored, and how to back it up

Progress lives in PostgreSQL, inside the Docker volume `todolist_tracker-pgdata`
— not in your browser. Signing in from another browser or machine shows the same
data, and clearing browser data loses nothing but your session.

Back up and restore:

```bash
docker exec learning-tracker-db pg_dump -U tracker tracker > backup.sql
cat backup.sql | docker exec -i learning-tracker-db psql -U tracker tracker
```

Only the login token is kept in the browser, purely so a reload does not sign you
out.

## Changing the default plan

`backend/app/data/default_plan.py` is the template copied into each **new**
account. Editing it never affects existing users — they own their own copy and
edit it in the app, under **Edit plan**.

## Schema changes

Tables are created at startup from the models. For changes to tables that already
hold data, use Alembic so nothing is lost:

```bash
cd backend
./.venv/bin/alembic revision --autogenerate -m "add notes to topic_progress"
./.venv/bin/alembic upgrade head
```
