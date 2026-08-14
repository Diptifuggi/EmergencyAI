import React, { createContext, useEffect, useState } from 'react'
import authService from '../services/authService'
import { getToken, setToken, clearAuth, getUser as storageGetUser, setUser as storageSetUser } from '../utils/storage'
import { decodeJwt } from '../utils/helpers'

const AuthContext = createContext()

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    if (token) {
      const stored = storageGetUser()
      if (stored) setUser(stored)
    }
    setLoading(false)
  }, [])

  const login = async (credentials) => {
    const res = await authService.login(credentials)
    const data = res.data
    setToken(data.access_token, data.refresh_token)
    // decode user information from token when available
    const payload = decodeJwt(data.access_token)
    const userObj = payload ? { id: payload.sub, role: payload.role } : null
    storageSetUser(userObj)
    setUser(userObj)
    return data
  }

  const logout = async () => {
    try {
      await authService.logout()
    } catch (e) {
      // ignore
    }
    clearAuth()
    setUser(null)
  }

  const value = { user, loading, login, logout }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export default AuthContext
