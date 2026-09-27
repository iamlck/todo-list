import { useState } from 'react'
import { api } from '../api/client'
import { useUndo } from '../context/UndoContext'

/** Edit one main task and its subtasks. */
export default function TaskEditor({ day, task, index, siblingCount, onChanged, onError, onMove }) {
  const { offerUndo } = useUndo()
  const [renaming, setRenaming] = useState(false)
  const [draft, setDraft] = useState(task.title)
  const [newSubtask, setNewSubtask] = useState('')
  const [editingSub, setEditingSub] = useState(null)
  const [subDraft, setSubDraft] = useState('')

  const subtasks = task.subtasks ?? []

  async function run(work) {
    try {
      await work()
      await onChanged()
    } catch (err) {
      onError(err.message)
    }
  }

  function snapshotOf(item, parentId) {
    return {
      day_id: day.id,
      parent_id: parentId,
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

  function removeTask() {
    const count = subtasks.length
    const detail = count ? ` and its ${count} subtasks` : ''
    if (!window.confirm(`Delete "${task.title}"${detail}?`)) return
    // Captured first, so undo can rebuild it with progress and time intact.
    const snapshot = snapshotOf(task, null)
    api
      .deleteTask(task.id)
      .then(async (result) => {
        await onChanged()
        offerUndo(`Deleted "${task.title}".`, async () => {
          // Passing the log ids stops the history claiming it is still gone.
          await api.restoreTask({ ...snapshot, deleted_log_ids: result?.deleted_log_ids ?? [] })
          await onChanged()
        })
      })
      .catch((err) => onError(err.message))
  }

  function removeSubtask(sub) {
    if (!window.confirm(`Delete "${sub.title}"?`)) return
    const snapshot = snapshotOf({ ...sub, subtasks: [] }, task.id)
    api
      .deleteTask(sub.id)
      .then(async (result) => {
        await onChanged()
        offerUndo(`Deleted "${sub.title}".`, async () => {
          await api.restoreTask({ ...snapshot, deleted_log_ids: result?.deleted_log_ids ?? [] })
          await onChanged()
        })
      })
      .catch((err) => onError(err.message))
  }

  function moveSubtask(i, delta) {
    const ids = subtasks.map((s) => s.id)
    const to = i + delta
    if (to < 0 || to >= ids.length) return
    ;[ids[i], ids[to]] = [ids[to], ids[i]]
    run(() => api.reorderTasks(day.id, task.id, ids))
  }

  return (
    <li className="task-editor">
      <div className="row wrap gap between">
        {renaming ? (
          <form
            className="row gap grow"
            onSubmit={(e) => {
              e.preventDefault()
              const title = draft.trim()
              if (!title) return
              setRenaming(false)
              run(() => api.renameTask(task.id, title))
            }}
          >
            <input aria-label="Task title" value={draft} onChange={(e) => setDraft(e.target.value)} autoFocus />
            <button type="submit" className="link">Save</button>
            <button type="button" className="link" onClick={() => setRenaming(false)}>Cancel</button>
          </form>
        ) : (
          <strong className="grow">{task.title}</strong>
        )}

        <div className="row gap">
          <button type="button" className="icon" aria-label={`Move "${task.title}" up`} disabled={index === 0} onClick={() => onMove(index, -1)}>↑</button>
          <button type="button" className="icon" aria-label={`Move "${task.title}" down`} disabled={index === siblingCount - 1} onClick={() => onMove(index, 1)}>↓</button>
          <button type="button" className="link" onClick={() => { setDraft(task.title); setRenaming(true) }}>Rename</button>
          <button type="button" className="link danger" onClick={removeTask}>Delete</button>
        </div>
      </div>

      {subtasks.length > 0 && (
        <ul className="editor-list">
          {subtasks.map((sub, i) => (
            <li key={sub.id}>
              {editingSub === sub.id ? (
                <form
                  className="row gap grow"
                  onSubmit={(e) => {
                    e.preventDefault()
                    const title = subDraft.trim()
                    if (!title) return
                    setEditingSub(null)
                    run(() => api.renameTask(sub.id, title))
                  }}
                >
                  <input aria-label="Subtask title" value={subDraft} onChange={(e) => setSubDraft(e.target.value)} autoFocus />
                  <button type="submit" className="link">Save</button>
                  <button type="button" className="link" onClick={() => setEditingSub(null)}>Cancel</button>
                </form>
              ) : (
                <>
                  <span className="grow">
                    {sub.title}
                    {sub.completed && <span className="badge done-badge">done</span>}
                  </span>
                  <button type="button" className="icon" aria-label={`Move "${sub.title}" up`} disabled={i === 0} onClick={() => moveSubtask(i, -1)}>↑</button>
                  <button type="button" className="icon" aria-label={`Move "${sub.title}" down`} disabled={i === subtasks.length - 1} onClick={() => moveSubtask(i, 1)}>↓</button>
                  <button type="button" className="link" onClick={() => { setEditingSub(sub.id); setSubDraft(sub.title) }}>Rename</button>
                  <button type="button" className="link danger" onClick={() => removeSubtask(sub)}>Delete</button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      <form
        className="row gap"
        onSubmit={(e) => {
          e.preventDefault()
          const title = newSubtask.trim()
          if (!title) return
          setNewSubtask('')
          run(() => api.addTask(day.id, title, task.id))
        }}
      >
        <input
          aria-label={`New subtask under ${task.title}`}
          placeholder="Add a subtask…"
          value={newSubtask}
          onChange={(e) => setNewSubtask(e.target.value)}
        />
        <button type="submit" className="secondary">Add</button>
      </form>
    </li>
  )
}
