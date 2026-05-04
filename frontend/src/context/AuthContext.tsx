import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import type { User } from '../types'
import { authApi } from '../api/endpoints'
import api from '../api/client'

interface AuthCtx {
  user: User | null
  token: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      api.get<User>('/auth/me').then((r) => {
        setUser(r.data)
        setLoading(false)
      }).catch(() => {
        setToken(null)
        setUser(null)
        localStorage.removeItem('token')
        setLoading(false)
      })
    } else {
      setLoading(false)
    }
  }, [token])

  const login = async (username: string, password: string) => {
    const t = await authApi.login({ username, password })
    localStorage.setItem('token', t)
    setToken(t)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
