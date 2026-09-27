// Pure helpers shared by the dashboard, day view and editor, so the numbers
// are computed one way only.
//
// A plan is days -> main tasks -> subtasks. Only *leaf* tasks count towards
// progress: a main task with subtasks is a container, and counting both it
// and its children would double-count the same work.

export function leafTasks(day) {
  return (day.tasks ?? []).flatMap((task) =>
    task.subtasks?.length ? task.subtasks : [task],
  )
}

export function allLeafTasks(days) {
  return days.flatMap(leafTasks)
}

function tally(tasks) {
  const total = tasks.length
  const completed = tasks.filter((t) => t.completed).length
  // An empty plan is 0%, not NaN.
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100)
  return { completed, total, percent }
}

export function overallProgress(days) {
  return tally(allLeafTasks(days))
}

export function dayProgress(day) {
  return tally(leafTasks(day))
}

export function taskProgress(task) {
  return tally(task.subtasks?.length ? task.subtasks : [task])
}

/** How many leaf tasks sit in each state, across the whole plan. */
export function statusCounts(days) {
  const counts = { 'not-started': 0, 'in-progress': 0, completed: 0 }
  for (const task of allLeafTasks(days)) {
    const state = task.status ?? (task.completed ? 'completed' : 'not-started')
    counts[state] = (counts[state] ?? 0) + 1
  }
  return counts
}

export function dayStatus(day) {
  const leaves = leafTasks(day)
  if (leaves.length === 0) return 'not-started'
  if (leaves.every((t) => t.completed)) return 'completed'
  // A day counts as underway as soon as anything on it has been started,
  // not only once something is finished.
  const touched = leaves.some(
    (t) => t.completed || t.status === 'in-progress' || (t.minutes_spent ?? 0) > 0,
  )
  return touched ? 'in-progress' : 'not-started'
}

export const STATUS_LABELS = {
  'not-started': 'Not started',
  'in-progress': 'In progress',
  completed: 'Completed',
}

// --- time ---------------------------------------------------------------

/** Minutes as "1h 25m", "45m", or "—" when nothing is recorded. */
export function formatMinutes(minutes) {
  if (!minutes) return '—'
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (!hours) return `${rest}m`
  return rest ? `${hours}h ${rest}m` : `${hours}h`
}

export function totalMinutes(days) {
  // Main tasks already include their subtasks' time, so only top-level rows
  // are summed to avoid counting the same minutes twice.
  return days.reduce(
    (sum, day) => sum + (day.tasks ?? []).reduce((s, t) => s + (t.minutes_spent ?? 0), 0),
    0,
  )
}

export function dayMinutes(day) {
  return (day.tasks ?? []).reduce((s, t) => s + (t.minutes_spent ?? 0), 0)
}

/** Minutes a running timer has accumulated since it started. */
export function minutesSince(isoString, now = Date.now()) {
  if (!isoString) return 0
  const started = new Date(isoString).getTime()
  if (Number.isNaN(started)) return 0
  return Math.max(0, Math.floor((now - started) / 60000))
}

// --- time reporting -----------------------------------------------------

/** Time per day, in plan order: [{ position, title, minutes }]. */
export function timePerDay(days) {
  return days.map((day) => ({
    id: day.id,
    position: day.position,
    title: day.title,
    minutes: dayMinutes(day),
  }))
}

/**
 * Total time grouped by main-task name, across every day.
 *
 * Grouped by title rather than id because the same heading — "AWS CloudOps" —
 * is a separate row on each day, and the useful question is how much went
 * into that subject overall.
 */
export function timeByMainTask(days) {
  const totals = new Map()
  for (const day of days) {
    for (const task of day.tasks ?? []) {
      const minutes = task.minutes_spent ?? 0
      const current = totals.get(task.title) ?? { title: task.title, minutes: 0, tasks: 0 }
      current.minutes += minutes
      current.tasks += task.subtasks?.length || 1
      totals.set(task.title, current)
    }
  }
  return [...totals.values()].sort((a, b) => b.minutes - a.minutes)
}

/** The individual tasks with the most time on them. */
export function longestTasks(days, limit = 10) {
  const rows = []
  for (const day of days) {
    for (const task of day.tasks ?? []) {
      const children = task.subtasks?.length ? task.subtasks : [task]
      for (const leaf of children) {
        if ((leaf.minutes_spent ?? 0) > 0) {
          rows.push({
            id: leaf.id,
            title: leaf.title,
            parent: task.subtasks?.length ? task.title : null,
            dayPosition: day.position,
            minutes: leaf.minutes_spent,
            completed: leaf.completed,
          })
        }
      }
    }
  }
  return rows.sort((a, b) => b.minutes - a.minutes).slice(0, limit)
}

/** Headline figures for the time report. */
export function timeSummary(days) {
  const perDay = timePerDay(days)
  const tracked = perDay.filter((d) => d.minutes > 0)
  const total = perDay.reduce((s, d) => s + d.minutes, 0)
  return {
    total,
    trackedDays: tracked.length,
    // Averaged over days you actually worked, not the whole plan — otherwise
    // an untouched day 20 drags the figure down and says nothing useful.
    averagePerTrackedDay: tracked.length ? Math.round(total / tracked.length) : 0,
    busiest: tracked.reduce((best, d) => (!best || d.minutes > best.minutes ? d : best), null),
  }
}

// --- carry-forward history ---------------------------------------------

/** "Carried forward twice, last from Day 3" — or null when it never was. */
export function carryLabel(task) {
  if (!task.carried_count) return null
  const times = task.carried_count === 1 ? 'once' : `${task.carried_count}×`
  const from = task.last_carried_from ? `, last from Day ${task.last_carried_from}` : ''
  return `Carried forward ${times}${from}`
}

// --- dates --------------------------------------------------------------

// Parse YYYY-MM-DD as a local date. `new Date('2026-09-01')` would be parsed
// as UTC and can land on the previous day in western timezones.
function parseLocalDate(value) {
  if (!value) return null
  const [year, month, day] = value.split('-').map(Number)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}

export function todayIso() {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

/**
 * Which day of the plan today falls on: 1 on the start date, clamped to the
 * length of the plan. Null when no start date has been chosen.
 */
export function currentDay(startDate, dayCount, today = todayIso()) {
  const start = parseLocalDate(startDate)
  const now = parseLocalDate(today)
  if (!start || !now || dayCount === 0) return null

  const msPerDay = 24 * 60 * 60 * 1000
  const elapsed = Math.floor((now - start) / msPerDay)
  return Math.min(Math.max(elapsed + 1, 1), dayCount)
}
