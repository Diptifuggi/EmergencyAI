import axiosClient from '@/api/axiosClient'
import type { EmergencyCallListResponse, EmergencyCallResponse } from '@/types/emergency'
import {
  callItemsFromResponse,
  normalizeCallCollection,
  normalizeEmergencyCall,
} from '@/lib/emergencyCallNormalizer'

export async function getEmergencies(params: Record<string, any> = {}): Promise<EmergencyCallResponse[]> {
  const response = await axiosClient.get<EmergencyCallListResponse>('/emergency-calls/', { params })
  return normalizeCallCollection(response.data) as EmergencyCallResponse[]
}

export async function getAllEmergencies(): Promise<EmergencyCallResponse[]> {
  const limit = 200
  const calls = new Map<string, EmergencyCallResponse>()
  let offset = 0
  let total: number | null = null

  while (total === null || offset < total) {
    const response = await axiosClient.get<EmergencyCallListResponse>('/emergency-calls/', {
      params: { limit, offset },
    })
    const page = callItemsFromResponse(response.data)
    const normalized = normalizeCallCollection(page) as EmergencyCallResponse[]
    normalized.forEach((call, index) => {
      const key = call.id ? String(call.id) : `unidentified-${offset + index}`
      if (!calls.has(key)) calls.set(key, call)
    })
    const pageTotal = Number(response.data?.total)
    total = Number.isFinite(pageTotal) && pageTotal >= 0 ? pageTotal : null
    if (page.length < limit || page.length === 0 || total === null) break
    offset += page.length
  }

  return [...calls.values()]
}

export async function getEmergency(id: string): Promise<EmergencyCallResponse> {
  const response = await axiosClient.get<EmergencyCallResponse>(`/emergency-calls/${encodeURIComponent(id)}`)
  return normalizeEmergencyCall(response.data) as EmergencyCallResponse
}

export async function updateEmergency(
  id: string,
  payload: Partial<EmergencyCallResponse>,
): Promise<EmergencyCallResponse> {
  const response = await axiosClient.patch<EmergencyCallResponse>(
    `/emergency-calls/${encodeURIComponent(id)}`,
    payload,
  )
  return normalizeEmergencyCall(response.data) as EmergencyCallResponse
}

export async function getEmergencyAnalytics(): Promise<Record<string, any>> {
  const response = await axiosClient.get<Record<string, any>>('/analytics/summary')
  return response.data
}
