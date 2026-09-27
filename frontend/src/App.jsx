import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import DayView from './components/DayView'
import PlanEditor from './components/PlanEditor'
import Login from './components/Login'
import Signup from './components/Signup'
import ForgotPassword from './components/ForgotPassword'
import ResetPassword from './components/ResetPassword'
import Account from './components/Account'
import Setup from './components/Setup'
import History from './components/History'
import TimeReport from './components/TimeReport'
import Admin from './components/Admin'
import RequirePlan from './components/RequirePlan'
import { AdminOnly, UserOnly } from './components/RoleRoute'
import ProtectedRoute from './components/ProtectedRoute'
import { PlanProvider } from './context/PlanContext'
import { UndoProvider } from './context/UndoContext'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route
        element={
          <ProtectedRoute>
            <PlanProvider>
              <UndoProvider>
                <Layout />
              </UndoProvider>
            </PlanProvider>
          </ProtectedRoute>
        }
      >
        <Route path="/setup" element={<UserOnly><Setup /></UserOnly>} />
        <Route path="/" element={<UserOnly><RequirePlan><Dashboard /></RequirePlan></UserOnly>} />
        <Route
          path="/day/:position"
          element={<UserOnly><RequirePlan><DayView /></RequirePlan></UserOnly>}
        />
        <Route
          path="/editor"
          element={<UserOnly><RequirePlan><PlanEditor /></RequirePlan></UserOnly>}
        />
        <Route
          path="/time"
          element={<UserOnly><RequirePlan><TimeReport /></RequirePlan></UserOnly>}
        />
        <Route path="/history" element={<UserOnly><History /></UserOnly>} />
        <Route path="/account" element={<Account />} />
        <Route path="/admin" element={<AdminOnly><Admin /></AdminOnly>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
