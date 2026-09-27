import { useUndo } from '../context/UndoContext'

export default function UndoBar() {
  const { pending, run, dismiss, busy } = useUndo()
  if (!pending) return null

  return (
    <div className="banner undo" role="status">
      <span>{pending.message}</span>
      <span className="row gap">
        <button type="button" className="link" onClick={run} disabled={busy}>
          {busy ? 'Undoing…' : 'Undo'}
        </button>
        <button type="button" className="link" onClick={dismiss} disabled={busy}>
          Dismiss
        </button>
      </span>
    </div>
  )
}
