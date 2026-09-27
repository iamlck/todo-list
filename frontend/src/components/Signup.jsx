import { Link } from 'react-router-dom'
import AuthForm from './AuthForm'
import { useAuth } from '../context/AuthContext'

export default function Signup() {
  const { signUp } = useAuth()
  return (
    <AuthForm
      title="Create an account"
      submitLabel="Create account"
      action={signUp}
      footer={
        <>
          You will start with the default 15-day plan, which is yours to edit.
          Already registered? <Link to="/login">Sign in</Link>.
        </>
      }
    />
  )
}
