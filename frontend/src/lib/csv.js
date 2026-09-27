// CSV parsing for plan uploads.
//
// Expected columns (header row required, order does not matter):
//   day, day_title, main_task, subtask
//
// One row per subtask. Repeat `day` and `main_task` across rows; a row with
// an empty `subtask` creates a main task with nothing under it yet.

export const TEMPLATE_HEADERS = ['day', 'day_title', 'main_task', 'subtask']

export const TEMPLATE_CSV = `day,day_title,main_task,subtask
1,Foundations,AWS CloudOps,Review the exam guide
1,Foundations,AWS CloudOps,Take a baseline practice test
1,Foundations,Kubernetes,Understand the architecture
2,Workloads,AWS CloudOps,CloudWatch metrics and alarms
2,Workloads,Kubernetes,Pods and Deployments
`

/** Split one CSV line, honouring quoted fields and doubled quotes. */
function splitLine(line) {
  const out = []
  let field = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i]
    if (inQuotes) {
      if (char === '"') {
        if (line[i + 1] === '"') {
          field += '"'
          i += 1
        } else {
          inQuotes = false
        }
      } else {
        field += char
      }
    } else if (char === '"') {
      inQuotes = true
    } else if (char === ',') {
      out.push(field)
      field = ''
    } else {
      field += char
    }
  }
  out.push(field)
  return out.map((f) => f.trim())
}

/**
 * Parse CSV text into the plan shape the API expects.
 * Returns { days, errors, rowCount } — errors are human-readable strings.
 */
export function parsePlanCsv(text) {
  const errors = []
  const lines = text
    .replace(/\r\n?/g, '\n')
    .split('\n')
    .filter((l) => l.trim() !== '')

  if (lines.length < 2) {
    return { days: [], errors: ['The file needs a header row and at least one row of data.'], rowCount: 0 }
  }

  const headers = splitLine(lines[0]).map((h) => h.toLowerCase())
  const missing = ['day', 'main_task'].filter((h) => !headers.includes(h))
  if (missing.length) {
    return {
      days: [],
      errors: [`Missing required column(s): ${missing.join(', ')}. Expected ${TEMPLATE_HEADERS.join(', ')}.`],
      rowCount: 0,
    }
  }

  const index = Object.fromEntries(headers.map((h, i) => [h, i]))
  // Keyed by day number so rows for the same day can appear anywhere.
  const days = new Map()
  let rowCount = 0

  lines.slice(1).forEach((line, i) => {
    const lineNumber = i + 2
    const cells = splitLine(line)
    const dayRaw = cells[index.day] ?? ''
    const dayNumber = Number(dayRaw)

    if (!Number.isInteger(dayNumber) || dayNumber < 1) {
      errors.push(`Line ${lineNumber}: "${dayRaw}" is not a day number.`)
      return
    }
    const mainTask = cells[index.main_task] ?? ''
    if (!mainTask) {
      errors.push(`Line ${lineNumber}: main_task is empty.`)
      return
    }

    rowCount += 1
    if (!days.has(dayNumber)) days.set(dayNumber, { title: '', tasks: new Map() })
    const day = days.get(dayNumber)

    const dayTitle = index.day_title !== undefined ? cells[index.day_title] ?? '' : ''
    if (dayTitle && !day.title) day.title = dayTitle

    if (!day.tasks.has(mainTask)) day.tasks.set(mainTask, [])
    const subtask = index.subtask !== undefined ? cells[index.subtask] ?? '' : ''
    if (subtask) day.tasks.get(mainTask).push(subtask)
  })

  // Days are renumbered 1..n on the server, so gaps in the file are fine —
  // only the relative order matters.
  const ordered = [...days.entries()].sort((a, b) => a[0] - b[0])
  return {
    days: ordered.map(([, day]) => ({
      title: day.title,
      tasks: [...day.tasks.entries()].map(([title, subtasks]) => ({ title, subtasks })),
    })),
    errors,
    rowCount,
  }
}
