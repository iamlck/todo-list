import { useState } from 'react'
import { usePlan } from '../context/PlanContext'

/**
 * Add a task without leaving the day you are working in.
 *
 * Collapsed to a single link until used, so it never competes with the
 * checkboxes for attention. `parentId` set adds a subtask under that task;
 * omitted adds a main task to the day.
 */
export default function AddTask({ dayId, parentId = null, label, placeholder }) {
  const { addTask } = usePlan()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    const trimmed = title.trim()
    if (!trimmed) return
    setBusy(true)
    try {
      await addTask(dayId, trimmed, parentId)
      // Cleared but left open, so several can be added in a row.
      setTitle('')
    } catch {
      /* the error banner already says what went wrong */
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <button type="button" className="link add-task-toggle" onClick={() => setOpen(true)}>
        + {label}
      </button>
    )
  }

  return (
    <form className="row gap add-task" onSubmit={submit}>
      <label className="visually-hidden" htmlFor={`add-${parentId ?? dayId}`}>
        {label}
      </label>
      <input
        id={`add-${parentId ?? dayId}`}
        placeholder={placeholder}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        autoFocus
      />
      <button type="submit" className="secondary" disabled={busy || !title.trim()}>
        {busy ? 'Adding…' : 'Add'}
      </button>
      <button
        type="button"
        className="link"
        onClick={() => {
          setTitle('')
          setOpen(false)
        }}
      >
        Done
      </button>
    </form>
  )
}
