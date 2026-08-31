// @ts-nocheck
import axiosInstance from './axios'

export async function getAnalytics(): Promise<any> {
  const resp = await axiosInstance.get('/analytics')
  return resp.data
}
