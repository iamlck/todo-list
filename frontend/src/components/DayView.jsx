import { Link, useParams } from 'react-router-dom'
import { usePlan } from '../context/PlanContext'
import DayNavigation from './DayNavigation'
import ProgressBar from './ProgressBar'
import TaskGroup from './TaskGroup'
import CarryForward from './CarryForward'
import {
  STATUS_LABELS,
  currentDay,
  dayMinutes,
  dayProgress,
  dayStatus,
  formatMinutes,
} from '../lib/progress'

export default function DayView() {
  const { position } = useParams()
  const { days, startDate } = usePlan()

  const dayNumber = Number(position)
  const day = days.find((d) => d.position === dayNumber)

  if (!day) {
    return (
      <div className="pad">
        <h1>No such day</h1>
        <p className="muted">
          This plan has {days.length} days. <Link to="/">Back to the dashboard</Link>.
        </p>
      </div>
    )
  }

  const status = dayStatus(day)
  const isToday = dayNumber === currentDay(startDate, days.length)

  return (
    <div className="pad stack">
      <DayNavigation position={dayNumber} dayCount={days.length} />

      <header className="card stack">
        <div className="row wrap gap between">
          <h1>
            Day {day.position}
            {day.title ? ` — ${day.title}` : ''}
          </h1>
          <span className={`status-pill ${status}`}>{STATUS_LABELS[status]}</span>
        </div>
        {isToday && <p className="muted">This is your planned day for today.</p>}
        <ProgressBar label="This day" {...dayProgress(day)} />
        <p className="muted small">Time spent today: {formatMinutes(dayMinutes(day))}</p>
        <CarryForward day={day} />
      </header>

      {day.tasks.length === 0 ? (
        <p className="muted pad">
          Nothing planned for this day yet. Add tasks in the{' '}
          <Link to="/editor">plan editor</Link>.
        </p>
      ) : (
        day.tasks.map((task) => <TaskGroup key={task.id} task={task} />)
      )}
    </div>
  )
}
