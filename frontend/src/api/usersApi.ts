// @ts-nocheck
import axiosClient from '@/api/axiosClient'
import { User, Role } from '@/types/user'

export async function listUsers(params = {}): Promise<User[]> {
  const resp = await axiosClient.get<User[]>('/users', { params })
  return resp.data
}

export async function createUser(data: Partial<User>): Promise<User> {
  const resp = await axiosClient.post<User>('/users', data)
  return resp.data
}

export async function updateUser(id: string, data: Partial<User>): Promise<User> {
  const resp = await axiosClient.patch<User>(`/users/${id}`, data)
  return resp.data
}

export async function listRoles(): Promise<Role[]> {
  const resp = await axiosClient.get<Role[]>('/roles')
  return resp.data
}

export default {
  listUsers,
  createUser,
  updateUser,
  listRoles,
}
