import { useState } from 'react'
import { api } from '../api/client'
import TaskEditor from './TaskEditor'
import { useUndo } from '../context/UndoContext'
import { dayProgress, formatMinutes, dayMinutes } from '../lib/progress'

export default function DayEditor({ day, index, dayCount, onChanged, onError, onMove }) {
  const { offerUndo } = useUndo()
  const [open, setOpen] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [draft, setDraft] = useState(day.title)
  const [newTask, setNewTask] = useState('')
  const { completed, total } = dayProgress(day)

  async function run(work) {
    try {
      await work()
      await onChanged()
    } catch (err) {
      onError(err.message)
    }
  }

  async function remove() {
    try {
      // Ask the server what this would destroy, so the warning is accurate
      // rather than a generic "are you sure".
      const impact = await api.dayDeleteImpact(day.id)
      const detail =
        impact.completed_tasks > 0 || impact.minutes_spent > 0
          ? `${impact.tasks} tasks, ${impact.completed_tasks} completed, ${formatMinutes(impact.minutes_spent)} recorded. That will be lost.`
          : `${impact.tasks} tasks. None are completed.`
      if (!window.confirm(`Delete Day ${day.position} "${day.title}"?\n\n${detail}`)) return

      // Snapshot first, so undo can rebuild the day with everything intact.
      const snapshot = {
        title: day.title,
        position: day.position,
        tasks: day.tasks.map((t) => ({
          day_id: day.id,
          parent_id: null,
          title: t.title,
          position: t.position,
          completed: t.completed,
          notes: t.notes ?? '',
          minutes_spent: t.subtasks?.length ? 0 : t.minutes_spent ?? 0,
          subtasks: (t.subtasks ?? []).map((s) => ({
            title: s.title,
            position: s.position,
            completed: s.completed,
            notes: s.notes ?? '',
            minutes_spent: s.minutes_spent ?? 0,
          })),
        })),
      }

      const result = await api.deleteDay(day.id)
      await onChanged()
      offerUndo(`Deleted Day ${snapshot.position}${day.title ? ` — ${day.title}` : ''}.`, async () => {
        await api.restoreDay({ ...snapshot, deleted_log_ids: result?.deleted_log_ids ?? [] })
        await onChanged()
      })
    } catch (err) {
      onError(err.message)
    }
  }

  function moveTask(i, delta) {
    const ids = day.tasks.map((t) => t.id)
    const to = i + delta
    if (to < 0 || to >= ids.length) return
    ;[ids[i], ids[to]] = [ids[to], ids[i]]
    run(() => api.reorderTasks(day.id, null, ids))
  }

  return (
    <li className="card day-editor">
      <div className="row wrap gap between">
        {renaming ? (
          <form
            className="row gap grow"
            onSubmit={(e) => {
              e.preventDefault()
              setRenaming(false)
              run(() => api.renameDay(day.id, draft.trim()))
            }}
          >
            <input
              aria-label={`Title for day ${day.position}`}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              autoFocus
            />
            <button type="submit" className="link">Save</button>
            <button type="button" className="link" onClick={() => setRenaming(false)}>Cancel</button>
          </form>
        ) : (
          <button
            type="button"
            className="disclosure grow"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            <strong>Day {day.position}</strong> {day.title || 'Untitled'}{' '}
            <span className="muted">
              · {completed}/{total} done · {formatMinutes(dayMinutes(day))}
            </span>
          </button>
        )}

        <div className="row gap">
          <button type="button" className="icon" aria-label={`Move day ${day.position} up`} disabled={index === 0} onClick={() => onMove(index, -1)}>↑</button>
          <button type="button" className="icon" aria-label={`Move day ${day.position} down`} disabled={index === dayCount - 1} onClick={() => onMove(index, 1)}>↓</button>
          <button type="button" className="link" onClick={() => { setDraft(day.title); setRenaming(true) }}>Rename</button>
          <button type="button" className="link danger" onClick={remove}>Delete</button>
        </div>
      </div>

      {open && (
        <div className="stack tracks">
          {day.tasks.length === 0 ? (
            <p className="muted">No tasks on this day yet.</p>
          ) : (
            <ul className="plain stack">
              {day.tasks.map((task, i) => (
                <TaskEditor
                  key={task.id}
                  day={day}
                  task={task}
                  index={i}
                  siblingCount={day.tasks.length}
                  onChanged={onChanged}
                  onError={onError}
                  onMove={moveTask}
                />
              ))}
            </ul>
          )}

          <form
            className="row gap"
            onSubmit={(e) => {
              e.preventDefault()
              const title = newTask.trim()
              if (!title) return
              setNewTask('')
              run(() => api.addTask(day.id, title, null))
            }}
          >
            <input
              aria-label={`New main task for day ${day.position}`}
              placeholder="Add a main task…"
              value={newTask}
              onChange={(e) => setNewTask(e.target.value)}
            />
            <button type="submit" className="secondary">Add</button>
          </form>
        </div>
      )}
    </li>
  )
}
