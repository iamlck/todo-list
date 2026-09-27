import { Link } from 'react-router-dom'
import AuthForm from './AuthForm'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { signIn } = useAuth()
  return (
    <AuthForm
      title="Sign in"
      submitLabel="Sign in"
      action={signIn}
      footer={
        <>
          <Link to="/forgot-password">Forgot your password?</Link>
          <br />
          No account yet? <Link to="/signup">Create one</Link>.
        </>
      }
    />
  )
}
