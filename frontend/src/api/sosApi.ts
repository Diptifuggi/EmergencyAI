// @ts-nocheck
import axiosClient from './axiosClient'

export interface SOSListItem {
  id: string
  alert_type: 'sos' | 'silent_sos' | 'panic_button'
  service_category?: string
  category_source?: string
  status: 'pending' | 'acknowledged' | 'verified' | 'cancelled' | 'closed' | 'false_alarm'
  user_id?: string
  user_name?: string
  user_phone?: string
  latitude?: number
  longitude?: number
  accuracy_m?: number
  location_status: 'available' | 'last_known' | 'denied' | 'unavailable'
  triggered_at: string
  received_at: string
  acknowledged_at?: string
  age_seconds?: number
}

export interface SOSListResponse {
  items: SOSListItem[]
  total: number
  page: number
  page_size: number
}

export interface SOSStats {
  active_sos: number
  silent_sos: number
  panic_button: number
  avg_time_to_acknowledge_seconds?: number
}

export interface ProfileSnapshot {
  user_id?: string
  username?: string
  email?: string
  full_name?: string
  phone?: string
  alternate_phone?: string
  guardian_phone?: string
  guardian_relation?: string
  address?: string
  age?: number
  blood_group?: string
  allergies?: string
  medical_history?: string
  medical_consent?: boolean
  profile_completed?: boolean
}

export interface SOSDetail {
  id: string
  idempotency_key: string
  user_id?: string
  alert_type: 'sos' | 'silent_sos' | 'panic_button'
  service_category?: string
  category_source?: string
  suggested_numbers?: string[]
  status: 'pending' | 'acknowledged' | 'verified' | 'cancelled' | 'closed' | 'false_alarm'
  latitude?: number
  longitude?: number
  accuracy_m?: number
  location_status: string
  triggered_at: string
  received_at: string
  battery_pct?: number
  network_type?: string
  device_id?: string
  app_version?: string
  acknowledged_by?: string
  acknowledged_at?: string
  verified_at?: string
  closed_at?: string
  cancelled_at?: string
  cancel_reason?: string
  close_reason?: string
  profile_snapshot?: ProfileSnapshot
  emergency_contacts?: Array<{
    id: string
    name: string
    phone: string
    relation: string
    notify_on_sos: boolean
    is_primary: boolean
  }>
  location_updates: Array<{
    id: string
    latitude: number
    longitude: number
    accuracy_m?: number
    recorded_at?: string
  }>
  events: Array<{
    id: string
    actor_type: string
    actor_id?: string
    event_type: string
    payload?: any
    created_at?: string
  }>
}

export async function getSosStats(): Promise<SOSStats> {
  const resp = await axiosClient.get<SOSStats>('/sos/stats')
  return resp.data
}

export async function listSosAlerts(params: {
  status?: string
  alert_type?: string
  service_category?: string
  page?: number
  page_size?: number
} = {}): Promise<SOSListResponse> {
  const resp = await axiosClient.get<SOSListResponse>('/sos', { params })
  return resp.data
}

export interface PublicTrackData {
  first_name?: string
  status: 'active' | 'ended' | 'expired'
  last_position?: {
    latitude: number
    longitude: number
    accuracy_m?: number
    recorded_at: string
  }
  updated_at?: string
  expires_at: string
}

export async function getPublicTrack(token: string): Promise<PublicTrackData> {
  const resp = await axiosClient.get<PublicTrackData>(`/public/track/${token}`)
  return resp.data
}

export async function listOperatorTrackSessions(): Promise<{ items: any[] }> {
  const resp = await axiosClient.get('/track/operator/active')
  return resp.data
}

export async function getOperatorTrackDetail(sessionId: string): Promise<any> {
  const resp = await axiosClient.get(`/track/operator/${sessionId}`)
  return resp.data
}

export async function getSosDetail(id: string): Promise<SOSDetail> {
  const resp = await axiosClient.get<SOSDetail>(`/sos/${id}`)
  return resp.data
}

export async function acknowledgeSos(id: string, note?: string): Promise<any> {
  const resp = await axiosClient.post(`/sos/${id}/ack`, { note })
  return resp.data
}

export async function verifySos(id: string, note?: string): Promise<any> {
  const resp = await axiosClient.post(`/sos/${id}/verify`, { note })
  return resp.data
}

export async function closeSos(id: string, note?: string): Promise<any> {
  const resp = await axiosClient.post(`/sos/${id}/close`, { note })
  return resp.data
}

export async function markFalseAlarmSos(id: string, note?: string): Promise<any> {
  const resp = await axiosClient.post(`/sos/${id}/false-alarm`, { note })
  return resp.data
}
