// Flattening the plan for analytics: one row per unit of work (a subtask, or
// a main task with nothing under it), the same rows progress is counted on.

import { taskState } from './progress'

export const EXPORT_COLUMNS = [
  ['day', 'Day'],
  ['date', 'Date'],
  ['day_title', 'Day title'],
  ['main_task', 'Main task'],
  ['subtask', 'Subtask'],
  ['status', 'Status'],
  ['completed', 'Completed'],
  ['minutes_spent', 'Minutes spent'],
  ['carried_count', 'Times carried'],
  ['original_day', 'Originally planned day'],
  ['started_at', 'Started at'],
  ['notes', 'Notes'],
]

function dateForDay(startDate, position) {
  if (!startDate) return ''
  const d = new Date(`${startDate}T00:00:00`)
  if (Number.isNaN(d.getTime())) return ''
  d.setDate(d.getDate() + position - 1)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function exportRows(days, startDate) {
  const rows = []
  for (const day of days) {
    for (const main of day.tasks ?? []) {
      const units = main.subtasks?.length ? main.subtasks : [main]
      for (const unit of units) {
        rows.push({
          day: day.position,
          date: dateForDay(startDate, day.position),
          day_title: day.title ?? '',
          main_task: main.title,
          subtask: unit === main ? '' : unit.title,
          status: taskState(unit),
          completed: unit.completed ? 'yes' : 'no',
          minutes_spent: unit.minutes_spent ?? 0,
          carried_count: unit.carried_count ?? 0,
          original_day: unit.original_day_position ?? '',
          started_at: unit.started_at ?? '',
          notes: unit.notes ?? '',
        })
      }
    }
  }
  return rows
}

function cell(value) {
  let text = String(value ?? '')
  // Stop spreadsheets treating a note that starts with = + - @ as a formula.
  if (/^[=+\-@]/.test(text) && Number.isNaN(Number(text))) text = `'${text}`
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function rowsToCsv(rows) {
  const header = EXPORT_COLUMNS.map(([, label]) => label).join(',')
  const lines = rows.map((r) => EXPORT_COLUMNS.map(([key]) => cell(r[key])).join(','))
  return [header, ...lines].join('\r\n') + '\r\n'
}

export function downloadFile(filename, content, type) {
  // The BOM makes Excel read a CSV as UTF-8.
  const blob = new Blob([type.includes('csv') ? '﻿' : '', content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
