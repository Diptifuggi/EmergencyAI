// @ts-nocheck
import axiosInstance from './axios'

export async function createDispatch(payload: Record<string, any>) {
  const resp = await axiosInstance.post('/dispatch', payload)
  return resp.data
}

export async function updateDispatch(id: string, payload: Record<string, any>) {
  const resp = await axiosInstance.put(`/dispatch/${id}`, payload)
  return resp.data
}
