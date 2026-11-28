// @ts-nocheck
import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
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

const INACTIVITY_LOGOUT_MS = 30 * 60 * 1000
const INACTIVITY_WARNING_MS = 29 * 60 * 1000

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [inactivityWarning, setInactivityWarning] = useState<boolean>(false)
  const warnTimerRef = useRef<any>(null)
  const logoutTimerRef = useRef<any>(null)

  const isAuthenticated = !!user

  async function login(email: string, password: string) {
    const data = await authApi.login(email, password)
    tokenStore.setTokens((data as any).access_token, (data as any).refresh_token || null)
    const me = await authApi.getMe()
    const role = (me?.role_name || '').toLowerCase()
    if (role === 'user') {
      await authApi.logout()
      setUser(null)
      throw new Error('Access denied: Citizen accounts must use the EmergencyIQ mobile app.')
    }
    setUser(me)
    return me
  }

  async function logout() {
    clearTimeout(warnTimerRef.current)
    clearTimeout(logoutTimerRef.current)
    setInactivityWarning(false)
    try { await authApi.logout() } catch (e) {}
    tokenStore.clearTokens()
    setUser(null)
  }

  // Restore session on mount
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
          if ((me?.role_name || '').toLowerCase() === 'user') {
            tokenStore.clearTokens()
          } else if (mounted) {
            setUser(me)
          }
        } catch (e) {
          tokenStore.clearTokens()
        }
      }
      if (mounted) setIsLoading(false)
    }
    restore()
    return () => { mounted = false }
  }, [])

  // 30-minute inactivity auto-logout with 1-minute warning
  useEffect(() => {
    if (!isAuthenticated) return

    const resetTimers = () => {
      setInactivityWarning(false)
      clearTimeout(warnTimerRef.current)
      clearTimeout(logoutTimerRef.current)
      warnTimerRef.current = setTimeout(() => setInactivityWarning(true), INACTIVITY_WARNING_MS)
      logoutTimerRef.current = setTimeout(() => { logout() }, INACTIVITY_LOGOUT_MS)
    }

    const events = ['mousemove', 'keydown', 'click', 'scroll']
    events.forEach(ev => window.addEventListener(ev, resetTimers))
    resetTimers()

    return () => {
      events.forEach(ev => window.removeEventListener(ev, resetTimers))
      clearTimeout(warnTimerRef.current)
      clearTimeout(logoutTimerRef.current)
    }
  }, [isAuthenticated])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
      {children}
      {inactivityWarning && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full shadow-xl space-y-4">
            <h3 className="text-lg font-bold text-zinc-900">Session Expiring Soon</h3>
            <p className="text-sm text-zinc-600">
              You have been inactive for 29 minutes. You will be automatically logged out in 1 minute.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={logout}
                className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded"
              >
                Logout Now
              </button>
              <button
                onClick={() => setInactivityWarning(false)}
                className="px-4 py-1.5 text-sm bg-black text-white rounded font-medium"
              >
                Stay Signed In
              </button>
            </div>
          </div>
        </div>
      )}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export default AuthContext
