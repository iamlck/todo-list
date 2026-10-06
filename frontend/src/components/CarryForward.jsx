import { useState } from 'react'
import { api } from '../api/client'
import { usePlan } from '../context/PlanContext'
import { useUndo } from '../context/UndoContext'
import { leafTasks } from '../lib/progress'

/**
 * Move unfinished tasks from this day to another one (earlier or later), or
 * delete them.
 *
 * You choose which tasks go: the picker opens with all of them selected,
 * since carrying everything is the common case, but each can be unticked to
 * leave it on this day.
 */
const PREVIOUS = '__previous'

export default function CarryForward({ day }) {
  const { days, carryForward, reload } = usePlan()
  const { offerUndo } = useUndo()

  // Leaves are the real units of work, so those are what you pick from.
  const unfinished = leafTasks(day).filter((t) => !t.completed)
  // Subtasks are shown with their main task, so you can see where each belongs.
  const parentTitle = new Map(
    (day.tasks ?? []).flatMap((m) => (m.subtasks ?? []).map((s) => [s.id, m.title])),
  )
  const others = days.filter((d) => d.id !== day.id)
  const nextDay = days.find((d) => d.position === day.position + 1)
  const prevDay = days.find((d) => d.position === day.position - 1)

  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState(() => new Set())
  const [target, setTarget] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  if (unfinished.length === 0) {
    return <p className="muted">Nothing left to carry forward — this day is complete.</p>
  }

  function openPicker() {
    // Everything preselected: unticking the few you want to keep is usually
    // less work than ticking the many you want to move.
    setSelected(new Set(unfinished.map((t) => t.id)))
    setError(null)
    setOpen(true)
  }

  function toggle(id) {
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function run() {
    if (selected.size === 0) {
      setError('Choose at least one task to carry forward.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const result = await carryForward(day.id, {
        taskIds: [...selected],
        targetDayId: target && target !== PREVIOUS ? target : null,
        direction: target === PREVIOUS ? 'previous' : 'next',
      })
      const noun = result.moved === 1 ? 'task' : 'tasks'
      setOpen(false)
      offerUndo(`Moved ${result.moved} ${noun} to Day ${result.target_day_position}.`, async () => {
        await api.moveTasks(result.moved_task_ids, day.id)
        await reload()
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  // Subtasks need their parent's id so a deletion can be restored in place.
  function snapshotOf(id) {
    for (const main of day.tasks ?? []) {
      const item = main.id === id ? main : (main.subtasks ?? []).find((s) => s.id === id)
      if (!item) continue
      return {
        day_id: day.id,
        parent_id: main.id === id ? null : main.id,
        title: item.title,
        position: item.position,
        completed: item.completed,
        notes: item.notes ?? '',
        minutes_spent: item.minutes_spent ?? 0,
        subtasks: (item.subtasks ?? []).map((s) => ({
          title: s.title,
          position: s.position,
          completed: s.completed,
          notes: s.notes ?? '',
          minutes_spent: s.minutes_spent ?? 0,
        })),
      }
    }
    return null
  }

  async function remove() {
    if (selected.size === 0) {
      setError('Choose at least one task to delete.')
      return
    }
    const noun = selected.size === 1 ? 'task' : 'tasks'
    if (!window.confirm(`Delete ${selected.size} ${noun}? You can undo this straight afterwards.`)) {
      return
    }
    setBusy(true)
    setError(null)
    const snapshots = []
    try {
      for (const id of selected) {
        const snapshot = snapshotOf(id)
        const result = await api.deleteTask(id)
        if (snapshot) snapshots.push({ ...snapshot, deleted_log_ids: result?.deleted_log_ids ?? [] })
      }
      setOpen(false)
      await reload()
      offerUndo(`Deleted ${snapshots.length} ${noun}.`, async () => {
        // Parents first, so restored subtasks have somewhere to go.
        for (const s of snapshots.sort((a, b) => (a.parent_id ? 1 : 0) - (b.parent_id ? 1 : 0))) {
          await api.restoreTask(s)
        }
        await reload()
      })
    } catch (err) {
      setError(err.message)
      await reload()
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <div className="carry">
        <button type="button" className="secondary" onClick={openPicker}>
          Move or delete…
        </button>
        <span className="muted small">
          {' '}
          {unfinished.length} unfinished {unfinished.length === 1 ? 'task' : 'tasks'}
        </span>
      </div>
    )
  }

  return (
    <div className="carry stack">
      <fieldset className="carry-picker">
        <legend>Choose the tasks</legend>

        <div className="row gap wrap carry-actions">
          <button
            type="button"
            className="link"
            onClick={() => setSelected(new Set(unfinished.map((t) => t.id)))}
          >
            Select all
          </button>
          <button type="button" className="link" onClick={() => setSelected(new Set())}>
            Clear
          </button>
          <span className="muted small">
            {selected.size} of {unfinished.length} selected
          </span>
        </div>

        <ul className="carry-list">
          {unfinished.map((topic) => {
            const id = `carry-topic-${topic.id}`
            return (
              <li key={topic.id}>
                <input
                  id={id}
                  type="checkbox"
                  checked={selected.has(topic.id)}
                  onChange={() => toggle(topic.id)}
                />
                <label htmlFor={id}>
                  {parentTitle.has(topic.id) && (
                    <span className="muted">{parentTitle.get(topic.id)} › </span>
                  )}
                  {topic.title}
                </label>
              </li>
            )
          })}
        </ul>
      </fieldset>

      <div className="row wrap gap">
        <label htmlFor={`carry-target-${day.id}`} className="muted">
          Move to
        </label>
        <select
          id={`carry-target-${day.id}`}
          value={target}
          onChange={(e) => setTarget(e.target.value)}
        >
          {prevDay && <option value={PREVIOUS}>Previous day (Day {prevDay.position})</option>}
          <option value="">
            {nextDay ? `Next day (Day ${nextDay.position})` : 'Next day — none, pick one'}
          </option>
          {others.map((d) => (
            <option key={d.id} value={d.id}>
              Day {d.position}
              {d.title ? ` — ${d.title}` : ''}
            </option>
          ))}
        </select>
        <button type="button" className="primary" onClick={run} disabled={busy}>
          {busy ? 'Working…' : `Move ${selected.size}`}
        </button>
        <button type="button" className="secondary danger" onClick={remove} disabled={busy}>
          Delete {selected.size}
        </button>
        <button type="button" className="secondary" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>

      <p className="muted small">
        Selected tasks move rather than being copied, and their notes travel with them.
        Anything left unticked stays on this day.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
