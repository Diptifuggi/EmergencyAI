import axiosClient from '@/api/axiosClient'

export async function getAnalytics(): Promise<any> {
  const response = await axiosClient.get('/analytics/summary')
  return response.data.analytics
}
