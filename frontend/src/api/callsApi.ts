// @ts-nocheck
import axiosClient from '@/api/axiosClient'
import { type AxiosProgressEvent } from 'axios'
import { EmergencyCall } from '@/types/call'

export async function listCalls(params: Record<string, any> = {}): Promise<EmergencyCall[]> {
  const resp = await axiosClient.get<EmergencyCall[]>('/calls', { params })
  return resp.data
}

export async function getCall(id: string): Promise<EmergencyCall> {
  const resp = await axiosClient.get<EmergencyCall>(`/calls/${id}`)
  return resp.data
}

export async function createCall(data: Partial<EmergencyCall>): Promise<EmergencyCall> {
  const resp = await axiosClient.post<EmergencyCall>('/calls', data)
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

export async function uploadAudio(callId: string, file: File, onUploadProgress?: (progressEvent: AxiosProgressEvent) => void): Promise<any> {
  const form = new FormData()
  form.append('file', file)
  const resp = await axiosClient.post(`/uploads/audio/${callId}`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
  return resp.data
}

export async function getPipelineStatus(callId: string): Promise<any> {
  const resp = await axiosClient.get(`/uploads/status/${callId}`)
  return resp.data
}

export async function runPipeline(callId: string): Promise<any> {
  const resp = await axiosClient.post(`/pipeline/run/${callId}`)
  return resp.data
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
