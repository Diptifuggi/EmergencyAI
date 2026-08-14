// @ts-nocheck
import React, { createContext, useContext, useEffect, useState } from 'react'
import * as authApi from '@/api/authApi'
import { tokenStore } from '@/api/axiosClient'
import { User } from '@/types/user'

type AuthContextType = {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<User | null>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const isAuthenticated = !!user

  async function login(email: string, password: string) {
    const data = await authApi.login(email, password)
    tokenStore.setTokens((data as any).access_token, (data as any).refresh_token || null)
    let me: any = null
    try {
      me = await authApi.getMe()
    } catch (e) {
      me = { email, username: email.split('@')[0] }
    }
    setUser(me)
    return me
  }

  async function logout() {
    try { await authApi.logout() } catch(e) {}
    tokenStore.clearTokens()
    setUser(null)
  }

  useEffect(() => {
    let mounted = true
    async function restore() {
      if (tokenStore.refreshToken) {
        try {
          const res = await authApi.refreshToken(tokenStore.refreshToken as string)
          tokenStore.setAccessToken((res as any).access_token)
          if ((res as any).refresh_token) {
            tokenStore.setRefreshToken((res as any).refresh_token)
          }
          const me = await authApi.getMe()
          if (mounted) setUser(me)
        } catch (e) {
          console.warn('Auth restore: refresh failed, keeping tokens until explicit logout')
        }
      }
      if (mounted) setIsLoading(false)
    }
    restore()
    return () => { mounted = false }
  }, [])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export default AuthContext
