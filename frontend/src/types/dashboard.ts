// @ts-nocheck
export interface DashboardMetrics {
  updated_at?: string
  total_calls?: number
  total_calls_delta?: number
  critical_calls?: number
  critical_calls_delta?: number
  todays_calls?: number
  todays_calls_delta?: number
  calls_by_status?: Record<string, number>
  active_incidents?: number
  active_incidents_delta?: number
  average_severity?: number
  average_severity_delta?: number
  call_rate?: { labels: string[]; values: number[] }
  event_status?: Record<string, number>
  calls_by_category_top5?: Array<{ name: string }>
  state_breakdown?: Array<{ state?: string; counts?: Record<string, number> }>
  severity_distribution?: Record<string, number>
  recent_critical_calls?: Array<{ id: string | number; caller_name?: string; phone?: string; time?: string; category?: string; priority?: string; score?: number; status?: string }>
  call_type_ratio?: Record<string, number>
}
