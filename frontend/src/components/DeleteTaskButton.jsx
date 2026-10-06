import { useState } from 'react'
import { api } from '../api/client'
import { usePlan } from '../context/PlanContext'
import { useUndo } from '../context/UndoContext'

/**
 * Delete one task, or a main task with all its subtasks, from the day it is
 * planned on. Undo rebuilds it with its notes, time and subtasks.
 */
export default function DeleteTaskButton({ task, dayId, parentId = null, label = 'Delete' }) {
  const { reload } = usePlan()
  const { offerUndo } = useUndo()
  const [error, setError] = useState(null)

  async function remove() {
    const count = task.subtasks?.length ?? 0
    const detail = count ? ` and its ${count} ${count === 1 ? 'subtask' : 'subtasks'}` : ''
    if (!window.confirm(`Delete "${task.title}"${detail}?`)) return
    // Captured first, so undo can restore progress and time as well.
    const snapshot = {
      day_id: dayId,
      parent_id: parentId,
      title: task.title,
      position: task.position,
      completed: task.completed,
      notes: task.notes ?? '',
      minutes_spent: task.minutes_spent ?? 0,
      subtasks: (task.subtasks ?? []).map((s) => ({
        title: s.title,
        position: s.position,
        completed: s.completed,
        notes: s.notes ?? '',
        minutes_spent: s.minutes_spent ?? 0,
      })),
    }
    try {
      const result = await api.deleteTask(task.id)
      await reload()
      offerUndo(`Deleted "${task.title}".`, async () => {
        await api.restoreTask({ ...snapshot, deleted_log_ids: result?.deleted_log_ids ?? [] })
        await reload()
      })
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <>
      <button type="button" className="link danger" onClick={remove}>
        {label}
      </button>
      {error && (
        <span className="error small" role="alert">
          {error}
        </span>
      )}
    </>
  )
}
