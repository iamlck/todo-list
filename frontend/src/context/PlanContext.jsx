import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from './AuthContext'

const PlanContext = createContext(null)

/**
 * Apply a patch to one task anywhere in the tree, returning new objects so
 * React sees the change. Ticking a main task ticks its subtasks, matching
 * what the server does.
 */
function applyToTree(task, taskId, patch) {
  if (task.id === taskId) {
    const updated = { ...task, ...patch }
    if ('completed' in patch && task.subtasks?.length) {
      updated.subtasks = task.subtasks.map((s) => ({ ...s, completed: patch.completed }))
    }
    return updated
  }
  if (!task.subtasks?.length) return task
  return { ...task, subtasks: task.subtasks.map((s) => applyToTree(s, taskId, patch)) }
}

export function PlanProvider({ children }) {
  const { isAuthenticated, user } = useAuth()
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setPlan(await api.getPlan())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // Administrators have no plan of their own, so there is nothing to fetch
    // and no reason to show them a loading state.
    if (isAuthenticated && user && !user.is_admin) reload()
    else if (!isAuthenticated || user?.is_admin) {
      setPlan(null)
      setLoading(false)
    }
  }, [isAuthenticated, user, reload])

  /**
   * Check a topic off. The UI updates at once and the request follows; if the
   * server rejects it, the change is rolled back and the error surfaced, so
   * the page never claims progress that was not saved.
   */
  const setCompleted = useCallback(
    async (taskId, completed) => {
      const previous = plan
      setPlan((current) => ({
        ...current,
        days: current.days.map((day) => ({
          ...day,
          tasks: day.tasks.map((task) => applyToTree(task, taskId, { completed })),
        })),
      }))
      try {
        await api.setCompleted(taskId, completed)
        setError(null)
      } catch (err) {
        setPlan(previous)
        setError(err.message)
      }
    },
    [plan],
  )

  /** Save a task's notes. The textarea already shows the text, so on
   *  failure we surface the error and reload rather than fighting the
   *  cursor by rewriting what the user is typing. */
  const saveNotes = useCallback(
    async (taskId, notes) => {
      setPlan((current) => ({
        ...current,
        days: current.days.map((day) => ({
          ...day,
          tasks: day.tasks.map((task) => applyToTree(task, taskId, { notes })),
        })),
      }))
      try {
        await api.setNotes(taskId, notes)
        setError(null)
      } catch (err) {
        setError(`Notes not saved: ${err.message}`)
      }
    },
    [],
  )

  const carryForward = useCallback(
    async (dayId, options) => {
      const result = await api.carryForward(dayId, options)
      await reload()
      return result
    },
    [reload],
  )

  const setStartDate = useCallback(async (startDate) => {
    try {
      await api.setStartDate(startDate || null)
      // Changing the start date only moves "today"; progress is untouched.
      setPlan((current) => ({ ...current, start_date: startDate || null }))
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }, [])

  const setStarted = useCallback(
    async (taskId, started) => {
      try {
        await api.setStarted(taskId, started)
        // Status rolls up to the main task, so re-read rather than trying to
        // recompute the tree in the browser.
        await reload()
      } catch (err) {
        setError(err.message)
      }
    },
    [reload],
  )

  const recordTime = useCallback(
    async (taskId, body) => {
      await api.setTime(taskId, body)
      // Minutes roll up through the tree, so re-read rather than trying to
      // recompute parents in the browser.
      await reload()
    },
    [reload],
  )

  const toggleTimer = useCallback(
    async (taskId, running) => {
      if (running) await api.stopTimer(taskId)
      else await api.startTimer(taskId)
      await reload()
    },
    [reload],
  )

  const value = {
    plan,
    days: plan?.days ?? [],
    onboarded: plan?.onboarded ?? false,
    startDate: plan?.start_date ?? null,
    loading,
    error,
    setError,
    reload,
    setCompleted,
    setStarted,
    saveNotes,
    recordTime,
    toggleTimer,
    carryForward,
    setStartDate,
  }

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>
}

export function usePlan() {
  const context = useContext(PlanContext)
  if (!context) throw new Error('usePlan must be used inside a PlanProvider')
  return context
}
