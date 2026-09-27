import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { usePlan } from '../context/PlanContext'
import DayEditor from './DayEditor'

export default function PlanEditor() {
  const { days, reload, setError } = usePlan()
  const [newDayTitle, setNewDayTitle] = useState('')

  async function move(index, delta) {
    const ids = days.map((d) => d.id)
    const target = index + delta
    if (target < 0 || target >= ids.length) return
    ;[ids[index], ids[target]] = [ids[target], ids[index]]
    try {
      await api.reorderDays(ids)
      await reload()
    } catch (err) {
      setError(err.message)
    }
  }

  async function addDay(event) {
    event.preventDefault()
    try {
      await api.addDay(newDayTitle.trim())
      setNewDayTitle('')
      await reload()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="pad stack">
      <section className="card stack">
        <h1>Edit your plan</h1>
        <p className="muted">
          This plan is yours alone. Renaming and reordering never affect what you have
          already ticked off — deleting does, and you will be warned first.{' '}
          <Link to="/">Back to the dashboard</Link>.
        </p>

        <form className="row gap" onSubmit={addDay}>
          <input
            aria-label="New day title"
            placeholder="New day title (optional)…"
            value={newDayTitle}
            onChange={(e) => setNewDayTitle(e.target.value)}
          />
          <button type="submit" className="primary">Add day</button>
        </form>
      </section>

      {days.length === 0 ? (
        <p className="muted pad">No days yet. Add your first one above.</p>
      ) : (
        <ul className="stack plain">
          {days.map((day, index) => (
            <DayEditor
              key={day.id}
              day={day}
              index={index}
              dayCount={days.length}
              onChanged={reload}
              onError={setError}
              onMove={move}
            />
          ))}
        </ul>
      )}
    </div>
  )
}
