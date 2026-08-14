// @ts-nocheck
import axiosClient from '@/api/axiosClient'
import { DashboardMetrics } from '@/types/dashboard'

export async function getSummary(): Promise<DashboardMetrics> {
  const resp = await axiosClient.get<DashboardMetrics>('/dashboard/summary')
  return resp.data
}

// compatibility alias for older components
export const getDashboard = getSummary

export default { getSummary }
