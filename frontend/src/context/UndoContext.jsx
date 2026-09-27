import { createContext, useCallback, useContext, useState } from 'react'

const UndoContext = createContext(null)

/**
 * Holds one pending undo at a time.
 *
 * The undo data lives in the running page, so it is offered until you navigate
 * away or perform another undoable action — long enough to catch a mistake,
 * without pretending to be a durable recycle bin.
 */
export function UndoProvider({ children }) {
  const [pending, setPending] = useState(null)
  const [busy, setBusy] = useState(false)

  // `undo` is an async function that reverses the action.
  const offerUndo = useCallback((message, undo) => {
    setPending({ message, undo })
  }, [])

  const dismiss = useCallback(() => setPending(null), [])

  const run = useCallback(async () => {
    if (!pending) return
    setBusy(true)
    try {
      await pending.undo()
      setPending(null)
    } finally {
      setBusy(false)
    }
  }, [pending])

  return (
    <UndoContext.Provider value={{ pending, offerUndo, dismiss, run, busy }}>
      {children}
    </UndoContext.Provider>
  )
}

export function useUndo() {
  const context = useContext(UndoContext)
  if (!context) throw new Error('useUndo must be used inside an UndoProvider')
  return context
}
