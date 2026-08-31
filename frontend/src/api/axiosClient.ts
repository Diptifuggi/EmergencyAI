import axios, { AxiosInstance, AxiosResponse, type AxiosRequestConfig, type AxiosRequestHeaders, type InternalAxiosRequestConfig } from 'axios'
import { API_BASE_URL } from '@/lib/constants'

interface TokenStore {
  accessToken: string | null
  refreshToken: string | null
  setTokens(access: string | null, refresh: string | null): void
  setAccessToken(access: string | null): void
  setRefreshToken(refresh: string | null): void
  clearTokens(): void
  initFromStorage(): void
}

export const tokenStore: TokenStore = {
  accessToken: null,
  refreshToken: null,
  setTokens(access, refresh) {
    this.accessToken = access
    this.refreshToken = refresh
    try {
      localStorage.setItem('accessToken', access || '')
      localStorage.setItem('refreshToken', refresh || '')
    } catch (e) {}
  },
  setAccessToken(access) {
    this.accessToken = access
    try { localStorage.setItem('accessToken', access || '') } catch (e) {}
  },
  setRefreshToken(refresh) {
    this.refreshToken = refresh
    try { localStorage.setItem('refreshToken', refresh || '') } catch (e) {}
  },
  clearTokens() {
    this.accessToken = null
    this.refreshToken = null
    try {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
    } catch (e) {}
  },
  initFromStorage() {
    try {
      const a = localStorage.getItem('accessToken') || null
      const r = localStorage.getItem('refreshToken') || null
      this.accessToken = a || null
      this.refreshToken = r || null
    } catch (e) { this.accessToken = null; this.refreshToken = null }
  }
}

// initialize from localStorage so sessions persist across page reloads
try { tokenStore.initFromStorage() } catch (e) {}

const axiosClient: AxiosInstance = axios.create({ baseURL: API_BASE_URL })

// REQUEST: attach Bearer token from tokenStore
axiosClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (tokenStore.accessToken) {
    config.headers.set('Authorization', `Bearer ${tokenStore.accessToken}`)
  }
  return config
})

// RESPONSE: on 401 attempt silent refresh once, then retry original request
let isRefreshing = false
let failQueue: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = []

axiosClient.interceptors.response.use(
  (res: AxiosResponse) => res,
  async err => {
    const orig = err.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    if (!orig) return Promise.reject(err)
    const status = err.response?.status
    if (status === 401 && !orig._retry && !(orig.url || '').includes('/auth/refresh')) {
      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failQueue.push({ resolve, reject })
        }).then((token) => {
          orig.headers.set('Authorization', `Bearer ${token}`)
          return axiosClient(orig)
        })
      }
      orig._retry = true
      isRefreshing = true
      try {
        const res = await axiosClient.post('/auth/refresh', {
          refresh_token: tokenStore.refreshToken
        })
        const newToken = res.data.access_token
        tokenStore.setAccessToken(newToken)
        failQueue.forEach(p => p.resolve(newToken))
        failQueue = []
        orig.headers.set('Authorization', `Bearer ${newToken}`)
        return axiosClient(orig)
      } catch (e) {
        failQueue.forEach(p => p.reject(e))
        failQueue = []
        tokenStore.clearTokens()
        return Promise.reject(e)
      } finally { isRefreshing = false }
    }
    return Promise.reject(err)
  }
)

export default axiosClient
