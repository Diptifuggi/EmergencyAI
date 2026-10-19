import axiosClient from '@/api/axiosClient'
import type { EmergencyCallListResponse, EmergencyCallResponse } from '@/types/emergency'

export async function getEmergencies(params: Record<string, any> = {}): Promise<EmergencyCallResponse[]> {
  const response = await axiosClient.get<EmergencyCallListResponse>('/emergency-calls/', { params })
  return response.data.items
}

export async function getEmergency(id: string): Promise<EmergencyCallResponse> {
  const response = await axiosClient.get<EmergencyCallResponse>(`/emergency-calls/${encodeURIComponent(id)}`)
  return response.data
}

export async function updateEmergency(
  id: string,
  payload: Partial<EmergencyCallResponse>,
): Promise<EmergencyCallResponse> {
  const response = await axiosClient.patch<EmergencyCallResponse>(
    `/emergency-calls/${encodeURIComponent(id)}`,
    payload,
  )
  return response.data
}

export async function getEmergencyAnalytics(): Promise<Record<string, any>> {
  const response = await axiosClient.get<Record<string, any>>('/analytics/summary')
  return response.data
}
