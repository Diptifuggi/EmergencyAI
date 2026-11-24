import { normalizeEmergencyCall } from '@/lib/emergencyCallNormalizer'

export interface EmergencyAnalysis {
  emergency_type?: string | null
  severity?: string | null
  priority_score?: number | null
  priority_level?: string | null
  confidence?: number | null
  human_confirmation_required?: boolean | null
  panic_score?: number | null
  panic_level?: string | null
  stress_score?: number | null
  stress_level?: string | null
  emergency_keywords?: string[] | null
  help_required?: string[] | null
  dispatch_recommendation?: {
    recommended_units?: string[] | null
    reason?: string | null
    priority_reason?: string | null
    dispatcher_action?: string | null
  } | null
  [key: string]: any
}

export interface EmergencyCallResponse {
  id: string
  user_id?: string | null
  call_type: string
  text_content?: string | null
  requested_language?: string | null
  language?: string | null
  status: string
  priority: string
  audio_file_path?: string | null
  original_audio_filename?: string | null
  audio_content_type?: string | null
  audio_file_size?: number | null
  audio_url?: string | null
  transcription?: string | null
  source?: string | null
  client_metadata?: Record<string, any> | null
  latitude?: number | null
  longitude?: number | null
  location_accuracy?: number | null
  location_timestamp?: string | null
  location_address?: string | null
  location_address_status?: string | null
  location_status?: string | null
  map_snapshot_available?: boolean
  map_snapshot_url?: string | null
  created_at?: string | null
  updated_at?: string | null
  location?: {
    latitude?: number | null
    longitude?: number | null
    accuracy_meters?: number | null
    captured_at?: string | null
    location_available?: boolean
    status?: string | null
    address_status?: string | null
    reason?: string | null
  } | null
}

export interface EmergencyCallListResponse {
  items: EmergencyCallResponse[]
  total: number
  limit: number
  offset: number
  api_version?: string
}

export function analysisForCall(call: EmergencyCallResponse): EmergencyAnalysis {
  return normalizeEmergencyCall(call).analysis as EmergencyAnalysis
}

export function categoryForCall(call: EmergencyCallResponse): string {
  const type = normalizeEmergencyCall(call).category
  if (!type) return 'Not available'
  return String(type).replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase())
}

export function priorityForCall(call: EmergencyCallResponse): string {
  const level = normalizeEmergencyCall(call).priority
  if (!level || level === 'Normal') return 'Not available'
  return level
}

export function locationForCall(call: EmergencyCallResponse): string {
  const normalized = normalizeEmergencyCall(call)
  if (normalized.locationAddress) return normalized.locationAddress
  if (normalized.latitude !== null && normalized.longitude !== null) {
    return `${normalized.latitude.toFixed(5)}, ${normalized.longitude.toFixed(5)}`
  }
  return 'Not available'
}

export function rawTranscriptForCall(call: EmergencyCallResponse): string | null {
  return normalizeEmergencyCall(call).textContent
}

export function cleanTranscriptForCall(call: EmergencyCallResponse): string | null {
  return normalizeEmergencyCall(call).cleanTranscript
}

export function transcriptForCall(call: EmergencyCallResponse): string | null {
  const normalized = normalizeEmergencyCall(call)
  return normalized.cleanTranscript || normalized.originalTranscript
}

export function toEmergencyCallRow(call: EmergencyCallResponse) {
  const priority = priorityForCall(call)
  const priorityStyles: Record<string, { bg: string; text: string; dot: string; border: string }> = {
    Critical: { bg: 'bg-red-100', text: 'text-red-800', dot: 'bg-red-600', border: 'border-l-red-600' },
    High: { bg: 'bg-amber-100', text: 'text-amber-800', dot: 'bg-amber-500', border: 'border-l-amber-500' },
    Moderate: { bg: 'bg-green-100', text: 'text-green-800', dot: 'bg-green-600', border: 'border-l-green-600' },
    Low: { bg: 'bg-blue-100', text: 'text-blue-800', dot: 'bg-blue-500', border: 'border-l-blue-500' },
  }
  const normalized = normalizeEmergencyCall(call)
  const statusValue = typeof normalized.status === 'string' ? normalized.status : 'Not available'
  const status = statusValue.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase())
  const statusStyles: Record<string, { bg: string; text: string }> = {
    Analyzed: { bg: 'bg-green-100', text: 'text-green-800' },
    Received: { bg: 'bg-zinc-100', text: 'text-zinc-700' },
    Analyzing: { bg: 'bg-yellow-100', text: 'text-yellow-800' },
    'Pending Transcription': { bg: 'bg-yellow-100', text: 'text-yellow-800' },
    'Analysis Failed': { bg: 'bg-red-100', text: 'text-red-800' },
  }
  const style = priorityStyles[priority] || { bg: 'bg-zinc-100', text: 'text-zinc-700', dot: 'bg-zinc-500', border: 'border-l-transparent' }
  const statusStyle = statusStyles[status] || { bg: 'bg-zinc-100', text: 'text-zinc-700' }
  const timestamp = normalized.createdAt ? new Date(normalized.createdAt) : null
  const elapsedMinutes = timestamp && !Number.isNaN(timestamp.getTime())
    ? Math.max(0, Math.floor((Date.now() - timestamp.getTime()) / 60000))
    : null
  const timeAgo = elapsedMinutes == null
    ? 'Not available'
    : elapsedMinutes < 1
      ? 'Just now'
      : elapsedMinutes < 60
        ? `${elapsedMinutes}m ago`
        : `${Math.floor(elapsedMinutes / 60)}h ago`
  return {
    id: call.id,
    caller_name: normalized.callerName || 'Caller not identified',
    caller_phone: normalized.callerPhone || 'Not provided',
    category: categoryForCall(call),
    priority_level: priority,
    priority_bg: style.bg,
    priority_text: style.text,
    dot: style.dot,
    border: style.border,
    location: locationForCall(call),
    time_ago: timeAgo,
    status,
    status_bg: statusStyle.bg,
    status_text: statusStyle.text,
  }
}
