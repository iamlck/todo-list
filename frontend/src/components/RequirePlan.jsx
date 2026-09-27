import { Navigate } from 'react-router-dom'
import { usePlan } from '../context/PlanContext'

/**
 * Sends an account with no plan to the setup screen, so a new user never
 * lands on an empty dashboard wondering what to do.
 */
export default function RequirePlan({ children }) {
  const { loading, onboarded, days } = usePlan()
  if (loading) return null
  if (!onboarded && days.length === 0) return <Navigate to="/setup" replace />
  return children
}
