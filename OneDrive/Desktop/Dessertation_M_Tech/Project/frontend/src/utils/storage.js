const TOKEN_KEY = 'eiq_token'
const REFRESH_KEY = 'eiq_refresh'
const USER_KEY = 'eiq_user'

export function setToken(token, refresh) {
  localStorage.setItem(TOKEN_KEY, token)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

export function setUser(user) {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user || null))
  } catch (e) {}
}

export function getUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(USER_KEY)
}
