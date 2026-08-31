// @ts-nocheck
import { format, formatDistanceToNow } from 'date-fns'

export function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  try { return format(new Date(iso), 'dd LLL yyyy, HH:mm') } catch { return iso }
}

export function formatDateAgo(iso?: string | null): string {
  if (!iso) return '—'
  try { return formatDistanceToNow(new Date(iso), { addSuffix: true }) } catch { return '—' }
}

export function formatUUID(uuid?: string | null): string {
  if (!uuid) return '—'
  return uuid.toString().slice(0,8) + '...'
}

export function formatScore(n?: number | null): string {
  return typeof n === 'number' ? n.toFixed(1) : '—'
}

export function formatFileSize(bytes?: number | null): string {
  if (bytes === undefined || bytes === null) return '—'
  const units = ['B','KB','MB','GB']
  let i = 0
  let v = bytes
  while (v >= 1024 && i < units.length-1) { v /= 1024; i++ }
  return `${v.toFixed(1)} ${units[i]}`
}

export function formatDuration(secs?: number | null): string {
  if (secs === undefined || secs === null) return '—'
  const m = Math.floor(secs/60); const s = Math.floor(secs%60)
  return `${m}m ${s}s`
}

export function getScoreColor(score: number): string {
  if (score >= 90) return '#b91c1c' // critical
  if (score >= 75) return '#ea580c' // very high
  if (score >= 50) return '#f59e0b' // high
  if (score >= 25) return '#10b981' // moderate
  return '#3b82f6' // low
}

export function formatNumber(value?: number | null): string {
  if (value === undefined || value === null) return '0'
  return value.toLocaleString()
}

const formatters = {
  formatDate,
  formatDateAgo,
  formatUUID,
  formatScore,
  formatNumber,
  number: formatNumber,
  formatFileSize,
  formatDuration,
  getScoreColor,
}

export default formatters
