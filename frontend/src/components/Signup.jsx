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
          Next you will choose how to start: the built-in 20-day plan, a number of
          empty days, or a spreadsheet you already have. Everything stays editable.
          Already registered? <Link to="/login">Sign in</Link>.
        </>
      }
    />
  )
}
