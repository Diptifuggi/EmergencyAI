// @ts-nocheck
import axiosClient from '@/api/axiosClient'
import { type AxiosProgressEvent } from 'axios'
import { EmergencyCall } from '@/types/call'
import { getEmergencies, getEmergency } from '@/api/emergencyApi'

export async function listCalls(params: Record<string, any> = {}): Promise<EmergencyCall[]> {
  return getEmergencies(params) as unknown as EmergencyCall[]
}

export async function getCall(id: string): Promise<EmergencyCall> {
  return getEmergency(id) as unknown as Promise<EmergencyCall>
}

export async function createCall(data: Partial<EmergencyCall>): Promise<EmergencyCall> {
  const resp = await axiosClient.post<EmergencyCall>('/emergency-calls/manual', data)
  return resp.data
}

export async function updateCall(id: string, data: Partial<EmergencyCall>): Promise<EmergencyCall> {
  const resp = await axiosClient.patch<EmergencyCall>(`/calls/${id}`, data)
  return resp.data
}

export async function deleteCall(id: string): Promise<any> {
  const resp = await axiosClient.delete(`/calls/${id}`)
  return resp.data
}

export async function uploadAudio(callId: string, file: File, onUploadProgress?: (progressEvent: AxiosProgressEvent) => void, signal?: AbortSignal): Promise<any> {
  const form = new FormData()
  form.append('file', file)
  form.append('language', 'auto')
  form.append('source', 'react_operator')
  form.append('existing_call_id', callId)
  const resp = await axiosClient.post('/emergency-calls/audio', form, {
    signal,
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
  return resp.data
}

export async function getPipelineStatus(callId: string): Promise<any> {
  throw new Error('Pipeline status is not exposed by the current backend.')
}

export async function runPipeline(callId: string): Promise<any> {
  throw new Error('Pipeline execution is triggered by emergency call creation.')
}

export default {
  listCalls,
  getCall,
  createCall,
  updateCall,
  deleteCall,
  uploadAudio,
  getPipelineStatus,
  runPipeline,
}
