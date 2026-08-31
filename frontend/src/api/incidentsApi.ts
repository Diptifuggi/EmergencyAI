// @ts-nocheck
import axiosClient from '@/api/axiosClient'
import { Incident } from '@/types/incident'

export async function listIncidents(params: Record<string, any> = {}): Promise<Incident[]> {
  const resp = await axiosClient.get<Incident[]>('/incidents', { params })
  return resp.data
}

export async function getIncident(id: string): Promise<Incident> {
  const resp = await axiosClient.get<Incident>(`/incidents/${id}`)
  return resp.data
}

export async function closeIncident(id: string): Promise<any> {
  const resp = await axiosClient.patch(`/incidents/${id}/close`)
  return resp.data
}

export async function createDispatch(incidentId: string, data: Record<string, any>): Promise<any> {
  const resp = await axiosClient.post(`/incidents/${incidentId}/dispatch`, data)
  return resp.data
}

export default {
  listIncidents,
  getIncident,
  closeIncident,
  createDispatch,
}
