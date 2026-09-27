import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, getToken, setToken, setUnauthorizedHandler } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => getToken())
  const [user, setUser] = useState(null)

  const signOut = useCallback(() => {
    setToken(null)
    setTokenState(null)
    setUser(null)
  }, [])

  // An expired token found by any request lands the user back on the sign-in
  // screen, rather than leaving a half-broken page.
  useEffect(() => {
    setUnauthorizedHandler(signOut)
  }, [signOut])

  // On a reload we still hold the token but not the account it belongs to, so
  // fetch it back. A rejected token signs out through the handler above.
  useEffect(() => {
    if (!token || user) return
    let cancelled = false
    api
      .me()
      .then((me) => {
        if (!cancelled) setUser(me)
      })
      .catch(() => {
        /* handled by the 401 handler; nothing extra to do */
      })
    return () => {
      cancelled = true
    }
  }, [token, user])

  const accept = useCallback((result) => {
    setToken(result.access_token)
    setTokenState(result.access_token)
    setUser(result.user)
  }, [])

  const value = useMemo(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token),
      signIn: async (email, password) => accept(await api.login(email, password)),
      signUp: async (email, password) => accept(await api.signup(email, password)),
      // Used by the password-reset screen, which receives a token of its own.
      acceptSession: accept,
      signOut,
    }),
    [token, user, accept, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside an AuthProvider')
  return context
}
