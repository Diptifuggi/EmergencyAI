export interface EmergencyAnalysis {
  emergency_type?: string | null
  priority_score?: number | null
  priority_level?: string | null
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

function normalizeAnalysisPayload(raw: any): EmergencyAnalysis {
  if (!raw || typeof raw !== 'object') return {}

  if ('analysis' in raw && raw.analysis && typeof raw.analysis === 'object') {
    return raw.analysis as EmergencyAnalysis
  }

  return raw as EmergencyAnalysis
}

export function analysisForCall(call: EmergencyCallResponse): EmergencyAnalysis {
  const metadata = call.client_metadata && typeof call.client_metadata === 'object' ? call.client_metadata : {}
  const result = metadata.emergency_analysis ?? metadata.analysis ?? {}
  return normalizeAnalysisPayload(result)
}

export function categoryForCall(call: EmergencyCallResponse): string {
  const type = analysisForCall(call).emergency_type || call.call_type
  if (!type) return 'Not available'
  return String(type).replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase())
}

export function priorityForCall(call: EmergencyCallResponse): string {
  const level = analysisForCall(call).priority_level || call.priority
  if (!level || String(level).toLowerCase() === 'normal') return 'Not available'
  return String(level).toLowerCase().replace(/\b\w/g, (character) => character.toUpperCase())
}

export function locationForCall(call: EmergencyCallResponse): string {
  if (typeof call.location_address === 'string' && call.location_address.trim()) return call.location_address
  const lat = call.location?.latitude ?? call.latitude
  const lng = call.location?.longitude ?? call.longitude
  if (lat != null && lng != null) {
    return `${Number(lat).toFixed(5)}, ${Number(lng).toFixed(5)}`
  }
  return 'Not available'
}

export function rawTranscriptForCall(call: EmergencyCallResponse): string | null {
  const text = typeof call.text_content === 'string' ? call.text_content.trim() : ''
  return text || null
}

export function cleanTranscriptForCall(call: EmergencyCallResponse): string | null {
  const transcription = typeof call.transcription === 'string' ? call.transcription.trim() : ''
  if (transcription) return transcription
  return rawTranscriptForCall(call)
}

export function transcriptForCall(call: EmergencyCallResponse): string | null {
  return cleanTranscriptForCall(call)
}

export function toEmergencyCallRow(call: EmergencyCallResponse) {
  const priority = priorityForCall(call)
  const priorityStyles: Record<string, { bg: string; text: string; dot: string; border: string }> = {
    Critical: { bg: 'bg-red-100', text: 'text-red-800', dot: 'bg-red-600', border: 'border-l-red-600' },
    High: { bg: 'bg-amber-100', text: 'text-amber-800', dot: 'bg-amber-500', border: 'border-l-amber-500' },
    Moderate: { bg: 'bg-green-100', text: 'text-green-800', dot: 'bg-green-600', border: 'border-l-green-600' },
    Low: { bg: 'bg-blue-100', text: 'text-blue-800', dot: 'bg-blue-500', border: 'border-l-blue-500' },
  }
  const status = (call.status || 'Not available').replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase())
  const statusStyles: Record<string, { bg: string; text: string }> = {
    Analyzed: { bg: 'bg-green-100', text: 'text-green-800' },
    Received: { bg: 'bg-zinc-100', text: 'text-zinc-700' },
    Analyzing: { bg: 'bg-yellow-100', text: 'text-yellow-800' },
    'Pending Transcription': { bg: 'bg-yellow-100', text: 'text-yellow-800' },
    'Analysis Failed': { bg: 'bg-red-100', text: 'text-red-800' },
  }
  const style = priorityStyles[priority] || { bg: 'bg-zinc-100', text: 'text-zinc-700', dot: 'bg-zinc-500', border: 'border-l-transparent' }
  const statusStyle = statusStyles[status] || { bg: 'bg-zinc-100', text: 'text-zinc-700' }
  const timestamp = call.created_at ? new Date(call.created_at) : null
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
  const metadata = call.client_metadata || {}

  return {
    id: call.id,
    caller_name: typeof metadata.caller_name === 'string' ? metadata.caller_name : 'Not available',
    caller_phone: typeof metadata.caller_phone === 'string' ? metadata.caller_phone : 'Not available',
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
