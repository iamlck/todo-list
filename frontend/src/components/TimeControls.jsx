import { useEffect, useState } from 'react'
import { usePlan } from '../context/PlanContext'
import { formatMinutes, minutesSince } from '../lib/progress'

/** Timer plus manual entry for one task. */
export default function TimeControls({ task }) {
  const { recordTime, toggleTimer } = usePlan()
  const running = Boolean(task.timer_started_at)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(String(task.minutes_spent ?? 0))
  const [, setTick] = useState(0)

  // Re-render each minute so a running timer's figure stays current.
  useEffect(() => {
    if (!running) return
    const id = setInterval(() => setTick((n) => n + 1), 30000)
    return () => clearInterval(id)
  }, [running])

  const live = running ? minutesSince(task.timer_started_at) : 0
  const shown = (task.minutes_spent ?? 0) + live

  async function save(event) {
    event.preventDefault()
    const minutes = Number(draft)
    if (!Number.isFinite(minutes) || minutes < 0) return
    setEditing(false)
    await recordTime(task.id, { minutes_spent: Math.round(minutes) })
  }

  return (
    <div className="time-controls row gap wrap">
      <button
        type="button"
        className={running ? 'danger-button tiny' : 'secondary tiny'}
        onClick={() => toggleTimer(task.id, running)}
        aria-label={running ? `Stop the timer for ${task.title}` : `Start a timer for ${task.title}`}
      >
        {running ? '■ Stop' : '▶ Start'}
      </button>

      {editing ? (
        <form className="row gap" onSubmit={save}>
          <label className="visually-hidden" htmlFor={`minutes-${task.id}`}>
            Minutes spent on {task.title}
          </label>
          <input
            id={`minutes-${task.id}`}
            type="number"
            min={0}
            className="minutes-input"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            autoFocus
          />
          <button type="submit" className="link">
            Save
          </button>
          <button type="button" className="link" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </form>
      ) : (
        <button
          type="button"
          className="link time-value"
          onClick={() => {
            setDraft(String(task.minutes_spent ?? 0))
            setEditing(true)
          }}
          aria-label={`Time spent on ${task.title}: ${formatMinutes(shown)}. Edit.`}
        >
          {formatMinutes(shown)}
          {running && <span className="running-dot" aria-hidden="true" />}
        </button>
      )}
    </div>
  )
}
