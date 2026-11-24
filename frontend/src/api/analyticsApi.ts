import axiosClient from '@/api/axiosClient'

export async function getAnalytics(): Promise<any> {
  const response = await axiosClient.get('/analytics/summary')
  const payload = response.data
  return payload?.analytics ?? payload?.data?.analytics ?? payload
}
