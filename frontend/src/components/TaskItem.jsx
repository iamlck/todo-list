import { useEffect, useRef, useState } from 'react'
import { usePlan } from '../context/PlanContext'
import TimeControls from './TimeControls'
import { STATUS_LABELS, carryLabel, taskState } from '../lib/progress'

const SAVE_DELAY_MS = 700

/** One task row: checkbox, notes, time, and carry-forward history. */
export default function TaskItem({ task, isSubtask = false }) {
  const { setCompleted, setStarted, saveNotes } = usePlan()
  const [showNotes, setShowNotes] = useState(Boolean(task.notes))
  const [draft, setDraft] = useState(task.notes ?? '')
  const [saved, setSaved] = useState(false)
  // What is currently on the server, so an unchanged value is never re-sent.
  const lastSaved = useRef(task.notes ?? '')
  const inputId = `task-${task.id}`
  const carried = carryLabel(task)
  const status = taskState(task)

  // Save a moment after typing stops, rather than on every keystroke.
  useEffect(() => {
    if (draft === lastSaved.current) return
    const timer = setTimeout(async () => {
      await saveNotes(task.id, draft)
      lastSaved.current = draft
      setSaved(true)
    }, SAVE_DELAY_MS)
    return () => clearTimeout(timer)
  }, [draft, task.id, saveNotes])

  useEffect(() => {
    if (!saved) return
    const timer = setTimeout(() => setSaved(false), 1500)
    return () => clearTimeout(timer)
  }, [saved])

  return (
    <li className={`task${task.completed ? ' done' : ''}${isSubtask ? ' subtask' : ''}`}>
      <div className="task-row">
        <input
          id={inputId}
          type="checkbox"
          checked={task.completed}
          onChange={(e) => setCompleted(task.id, e.target.checked)}
        />
        <label htmlFor={inputId} className="task-title">
          {task.title}
          {carried && <span className="carried-badge" title={carried}>↷ {task.carried_count}</span>}
        </label>

        <span className={`status-pill tiny ${status}`}>{STATUS_LABELS[status]}</span>

        {!task.completed && (
          <button
            type="button"
            className="link"
            onClick={() => setStarted(task.id, status === 'not-started')}
          >
            {status === 'not-started' ? 'Start' : 'Not started'}
          </button>
        )}
        <TimeControls task={task} />
        <button
          type="button"
          className="link notes-toggle"
          aria-expanded={showNotes}
          onClick={() => setShowNotes((v) => !v)}
        >
          {task.notes ? 'Notes ●' : 'Notes'}
        </button>
      </div>

      {carried && <p className="muted small carried-line">{carried}</p>}

      {showNotes && (
        <div className="notes">
          <label className="visually-hidden" htmlFor={`${inputId}-notes`}>
            Notes for {task.title}
          </label>
          <textarea
            id={`${inputId}-notes`}
            rows={3}
            placeholder="Anything worth remembering — links, commands, questions…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <span className="muted note-status">
            {draft !== lastSaved.current ? 'Saving…' : saved ? 'Saved' : ''}
          </span>
        </div>
      )}
    </li>
  )
}
