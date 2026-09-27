import TaskItem from './TaskItem'
import AddTask from './AddTask'
import ProgressBar from './ProgressBar'
import { STATUS_LABELS, formatMinutes, taskProgress } from '../lib/progress'

/** A main task and its subtasks. */
export default function TaskGroup({ task, dayId }) {
  const progress = taskProgress(task)
  const hasSubtasks = Boolean(task.subtasks?.length)

  return (
    <section className="card stack">
      <div className="row wrap gap between">
        <h3>{task.title}</h3>
        <span className="row gap">
          <span className={`status-pill ${task.status ?? 'not-started'}`}>
            {STATUS_LABELS[task.status ?? 'not-started']}
          </span>
          <span className="muted small">{formatMinutes(task.minutes_spent)} spent</span>
        </span>
      </div>

      <ProgressBar label={task.title} {...progress} />

      {hasSubtasks ? (
        <ul className="tasks">
          {task.subtasks.map((sub) => (
            <TaskItem key={sub.id} task={sub} isSubtask />
          ))}
        </ul>
      ) : (
        // A main task with nothing under it is itself the unit of work.
        <ul className="tasks">
          <TaskItem task={task} />
        </ul>
      )}

      <AddTask
        dayId={dayId}
        parentId={task.id}
        label="Add a subtask"
        placeholder={`Another step for ${task.title}…`}
      />
    </section>
  )
}
