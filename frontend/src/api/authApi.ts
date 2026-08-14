// @ts-nocheck
import axiosClient, { tokenStore } from '@/api/axiosClient'
import { LoginRequest, LoginResponse, RegisterRequest } from '@/types/auth'

export async function login(email: string, password: string): Promise<LoginResponse> {
  const resp = await axiosClient.post<LoginResponse>('/auth/login', { email, password })
  const data = resp.data
  if (data.access_token) {
    tokenStore.setAccessToken(data.access_token)
  }
  if ((data as any).refresh_token) {
    tokenStore.setRefreshToken((data as any).refresh_token)
  }
  return data
}

export async function logout(): Promise<void> {
  try {
    await axiosClient.post('/auth/logout')
  } catch (e) {
    // best-effort
  } finally {
    tokenStore.clearTokens()
  }
}

export async function refreshToken(refreshTokenValue: string): Promise<LoginResponse> {
  const resp = await axiosClient.post<LoginResponse>('/auth/refresh', { refresh_token: refreshTokenValue })
  const data = resp.data
  if (data.access_token) {
    tokenStore.setAccessToken(data.access_token)
  }
  if ((data as any).refresh_token) {
    tokenStore.setRefreshToken((data as any).refresh_token)
  }
  return data
}

export async function getMe(): Promise<any> {
  const resp = await axiosClient.get('/auth/me')
  return resp.data
}

export async function register(username: string, email: string, password: string): Promise<any> {
  const resp = await axiosClient.post('/auth/register', { username, email, password })
  return resp.data
}

export async function changePassword(oldPassword: string, newPassword: string, confirmPassword: string): Promise<any> {
  const resp = await axiosClient.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
    confirm_password: confirmPassword,
  })
  return resp.data
}

const authApi = { login, logout, refreshToken, getMe, register, changePassword }
export default authApi
