# Learning Tracker — a complete guide

A guide to what this app does and how to use it. No technical background
assumed. If you want the developer material instead, see
[architecture.md](architecture.md) and [api.md](api.md).

---

## What it is

A private study tracker that runs on your own computer. You keep a plan made of
**days**, each holding **main tasks**, each holding **subtasks**. You tick things
off as you go, record how long they took, and move anything unfinished to
another day.

It was built around a 20-day plan for three subjects — AWS CloudOps, Kubernetes
and GenAI — but nothing is fixed to that. You can start from the built-in plan,
from a spreadsheet you already have, or from blank days you fill in yourself.

Two things worth being clear about:

- **It is a personal tracker, not an official certification tool.** Ticking
  every box does not mean you will pass an exam.
- **Your data lives on your machine**, in a database on your computer. It is not
  sent anywhere, and there is no cloud account behind it.

---

## Starting it up

The app has three parts: a database, a backend, and the page you look at. The
first two run in Docker; the third runs from a terminal.

```bash
docker-compose up -d       # database and backend
cd frontend && npm run dev # the app itself
```

Then open **http://localhost:5173**.

To stop: `docker-compose down`, and press Ctrl-C in the `npm run dev` terminal.
Stopping does not delete anything — your data is still there next time.

Full setup instructions, including the very first run, are in
[README.md](README.md).

---

## Accounts

You sign up with an email address and a password of at least eight characters.
The email is only an identifier; nothing is ever sent to it.

Each account is completely separate. Two people using the same installation
cannot see each other's plans, progress or notes.

### If you forget your password

Use **Forgot your password?** on the sign-in screen. Because there is no mail
server, the reset link is written into the backend's log rather than emailed.
Read it with:

```bash
docker-compose logs --tail=20 api
```

The link works once and expires after 30 minutes. Asking for a new one cancels
the previous.

If you would rather not use the browser, someone with terminal access can set a
password directly:

```bash
docker-compose exec api python scripts/set_password.py you@example.com
```

Either way your plan and progress are untouched.

### Changing your password

**Account → Change password.** It asks for your current password first.

---

## Setting up your plan

The first thing a new account sees is a choice of three starting points.

**1. Use the default plan.** Twenty days covering AWS CloudOps, Kubernetes and
GenAI — foundations, then services and security, then practice exams, a
capstone project, and the exam itself on day 20. Each day has the three
subjects as main tasks, with two or three subtasks under each.

**2. Choose a number of days.** Say how many, get that many empty days, and add
your own tasks as you go.

**3. Upload a spreadsheet.** For a plan you already have. Click **Download
template** to get a worked example, fill it in, and upload it.

The spreadsheet needs four columns:

| Column | What goes in it |
| --- | --- |
| `day` | a number: 1, 2, 3… |
| `day_title` | a name for the day, such as "Foundations" |
| `main_task` | the subject or heading, such as "Kubernetes" |
| `subtask` | one specific thing to do |

One row per subtask, repeating the day and main task across rows. Excel and
Google Sheets both save as CSV (**File → Save As** or **Download → CSV**).
Before anything is saved you see a preview — how many days, tasks and subtasks
were found, and any lines it could not read.

Whichever you choose, everything stays editable afterwards.

---

## Finding your way around

Along the top:

- **Dashboard** — the overview
- **Time** — where your hours went
- **Edit plan** — add, rename, reorder and delete days and tasks
- **History** — what you have deleted
- **Account** — your password, and deleting your account

### The dashboard

- A **start date** you choose. From it the app works out which day of the plan
  today is, highlights it, and offers **Continue today** to open it.
- **Overall progress** — how much of the plan is done.
- **A breakdown** — how many tasks are not started, in progress, and completed.
- **Total time recorded.**
- **Every day as a tile**, showing its status and time, colour-coded and
  labelled. Click one to open it.

Changing the start date only moves which day counts as "today". It never alters
anything you have ticked off.

---

## Working through a day

Open a day and you see its main tasks, each with its subtasks underneath. For
each task you can:

**Tick it off.** Ticking every subtask completes its main task automatically.
Ticking a main task ticks everything under it.

**Mark it started.** Press **Start** and it becomes *In progress*; press *Not
started* to clear that. Every task is in one of three states — Not started, In
progress, Completed — shown as a small label beside it.

**Record time.** Two ways, adding into one figure:

- **▶ Start** runs a timer; **■ Stop** adds the elapsed minutes. Only one timer
  runs at a time, so the same stretch is never counted twice, and finishing a
  task stops its timer.
- **Click the time itself** to type minutes straight in — for work done away
  from the app, or time you forgot to track.

**Write notes.** The **Notes** button opens a box that saves by itself a moment
after you stop typing. A task can have notes while still unticked, and a dot on
the button shows when notes exist.

Notes and recorded time stay with a task through renaming, reordering and being
moved to another day.

---

## Carrying work forward

Days rarely go to plan. When one runs out, press **Carry forward…** at the top
of the day. You get a list of everything unfinished, all ticked to begin with —
untick whatever should stay, choose which day it moves to (the next one unless
you say otherwise), and confirm.

A few things this does deliberately:

- Tasks **move** rather than being copied, so nothing appears twice and the old
  day can genuinely be finished.
- **Finished work never moves**, even if you select it. It stays on the day you
  did it.
- Notes and recorded time travel with the task.
- Carried work **joins the matching heading** on the destination day, so you get
  one "Kubernetes" section, not two.

Each task remembers this. A **↷** badge shows how many times it has slipped and
which day it last came from — useful for spotting what keeps getting pushed.

---

## Where your time went

The **Time** page gathers everything:

- **Total recorded**, **days worked**, **average per day worked**, and your
  **busiest day**.
- **A bar for each day** — click one to jump to it.
- **By subject** — main tasks of the same name added up across the whole plan,
  so "AWS CloudOps" gives one figure for all 20 days.
- **Longest tasks** — the ten individual tasks with the most time on them.

Two notes on the numbers. Main tasks already include their subtasks' time, so
totals count them once, not twice. And the average covers days you *actually
worked* — counting untouched days ahead of you would only make the figure
meaningless.

Every chart has a **Show as table** option if you would rather read the numbers.

---

## Editing your plan

**Edit plan** lets you reshape everything. Add days, rename them, move them up
and down, delete them. Open a day to add main tasks and subtasks, rename them,
reorder them, or remove them.

Renaming and reordering never affect what you have ticked off, how long it took,
or the notes you wrote. Deleting does — and you are warned first, with the
actual numbers: how many tasks, how many completed, how much time.

### Undo

After deleting a task or a day, or carrying work forward, an **Undo** bar
appears at the top of the page. Undo restores everything — the task, its
completion, its notes, its recorded time, and a day goes back to its original
position rather than the end.

Undo lasts until you move to another page or do something else undoable. It is a
safety net for a misclick, not long-term storage. Ticking a box is not covered,
because unticking it does the same job.

### History

**History** lists everything you have deleted, newest first: what it was, which
day it was on, its parent task, how many subtasks went with it, whether it was
completed, and how much time had been recorded against it.

This is a record, not a recycle bin — it tells you what happened but holds
nothing to bring back. If you use Undo, the entry is marked as restored so it
stops saying the task is gone.

---

## Two kinds of account

**Learner accounts** have everything above: the plan, the tracking, the time,
the history.

**Administrator accounts** manage people, not plans. An administrator sees a
**Users** page and nothing else — no dashboard, no tasks of their own. The two
jobs are separate, so one account does not do both. If you want to both study
and administer, use two accounts.

On the Users page an administrator can see every account: when it was created,
whether a plan is set up, how many days and tasks it holds, how many are done,
time recorded, and when it was last active. They can grant or remove
administrator rights, and delete an account.

**An administrator cannot read anyone's notes.** They see how much work an
account holds, never what is in it.

Administrator rights can only be granted from a terminal, so nobody can promote
themselves through the app:

```bash
docker-compose exec api python scripts/make_admin.py them@example.com
docker-compose exec api python scripts/make_admin.py them@example.com --remove
```

Two safeguards: you cannot remove your own rights, and the last administrator
cannot be removed — either would lock everyone out.

Making an account an administrator hides its tracker but **deletes nothing**. If
it is made a learner again, its plan and progress come back exactly as they
were.

---

## Deleting an account

**Account → Delete account** removes your account and everything on it. It shows
what will be lost first, then asks for both your password and your own email
address. Administrators can delete other accounts the same way, using their own
password and the other person's email.

**This cannot be undone**, and there is no history of it. Take a backup first if
the data might matter.

---

## Backing up

Everything lives in a database on your machine. To save a copy:

```bash
docker exec learning-tracker-db pg_dump -U tracker tracker > backup.sql
```

To put it back:

```bash
cat backup.sql | docker exec -i learning-tracker-db psql -U tracker tracker
```

Worth doing before anything irreversible — deleting an account, or clearing out
a large part of a plan.

Your browser only remembers that you are signed in. Clearing browser data signs
you out and loses nothing else, and signing in from another browser shows
exactly the same plan.

---

## What it deliberately does not do

Honest limits, so you are not left looking for them:

- **No reminders or notifications.** It does not email you or nudge you.
- **No sharing.** Plans are private to one account; there is no way to show one
  to somebody else or work on one together.
- **No mobile app.** The page works on a phone browser, but only on the machine
  running it unless you set that up yourself.
- **No links or attachments on tasks** — notes are plain text.
- **No export.** You cannot download your plan as a file yet; the database
  backup above is the way to keep a copy.
- **Deleted work is not recoverable** beyond Undo in the moment.
- **Undo does not survive a reload.**

---

## If something goes wrong

**The page will not load.** Check the parts are running: `docker-compose ps`
should show both as up, and the `npm run dev` terminal should still be going.

**"Your session has expired."** Sign in again — being signed out after a long
gap is normal.

**Something did not save.** A red bar appears at the top when a change fails to
reach the backend. A tick that did not save is undone, so the page never claims
progress it did not record. Notes are left as you typed them — your words are
not thrown away — so copy them somewhere before reloading. It usually means the
backend stopped; check `docker-compose logs --tail=20 api`.

**A timer was left running.** Stop it, then click the time and type the right
number of minutes.

**You cannot sign in and do not know the password.** Use the reset described
under *Accounts*.
