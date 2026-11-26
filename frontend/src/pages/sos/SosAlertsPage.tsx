// @ts-nocheck
import React, { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Siren,
  Volume2,
  VolumeX,
  Phone,
  Clock,
  MapPin,
  AlertTriangle,
  RefreshCw,
  Eye,
  CheckCircle,
  Filter,
  ShieldAlert,
} from 'lucide-react'

import { listSosAlerts, getSosStats, SOSListItem } from '@/api/sosApi'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui'

function formatDateTime(dateStr?: string | Date): string {
  if (!dateStr) return '-'
  const d = typeof dateStr === 'string' ? new Date(dateStr) : dateStr
  if (isNaN(d.getTime())) return '-'
  return `${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })} • ${d.toLocaleDateString([], { day: '2-digit', month: 'short' })}`
}

function formatDistanceToNow(dateStr?: string | Date): string {
  if (!dateStr) return '-'
  const d = typeof dateStr === 'string' ? new Date(dateStr) : dateStr
  if (isNaN(d.getTime())) return '-'
  const diffSec = Math.floor((Date.now() - d.getTime()) / 1000)
  if (diffSec < 60) return `${diffSec}s ago`
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}h ago`
  const diffDay = Math.floor(diffHour / 24)
  return `${diffDay}d ago`
}

export default function SosAlertsPage() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [soundEnabled, setSoundEnabled] = useState<boolean>(true)
  const previousPendingIdsRef = useRef<Set<string>>(new Set())

  // 1. Fetch Stats (Auto-poll 5s)
  const { data: stats } = useQuery({
    queryKey: ['sos', 'stats'],
    queryFn: getSosStats,
    refetchInterval: 5000,
  })

  // 2. Fetch Alerts list (Auto-poll 5s)
  const {
    data: alertsData,
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['sos', 'list', statusFilter, typeFilter],
    queryFn: () =>
      listSosAlerts({
        status: statusFilter || undefined,
        alert_type: typeFilter || undefined,
        page_size: 50,
      }),
    refetchInterval: 5000,
  })

  const alerts = alertsData?.items || []

  // Beep sound generator for new pending SOS alerts
  const playAlertSound = () => {
    if (!soundEnabled) return
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sawtooth'
      osc.frequency.setValueAtTime(880, ctx.currentTime) // A5
      osc.frequency.setValueAtTime(440, ctx.currentTime + 0.15)
      gain.gain.setValueAtTime(0.3, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start()
      osc.stop(ctx.currentTime + 0.3)
    } catch (_) {}
  }

  // Detect newly arrived pending alerts and play sound
  useEffect(() => {
    if (!alerts) return
    const pendingAlerts = alerts.filter((a) => a.status === 'pending')
    const currentPendingIds = new Set(pendingAlerts.map((a) => a.id))

    // Check if there is an id not seen in previous set
    const hasNew = [...currentPendingIds].some((id) => !previousPendingIdsRef.current.has(id))
    if (hasNew && previousPendingIdsRef.current.size > 0) {
      playAlertSound()
    }
    previousPendingIdsRef.current = currentPendingIds
  }, [alerts, soundEnabled])

  const renderTypeBadge = (type: string) => {
    switch (type) {
      case 'sos':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-600 text-white shadow-sm">
            <span className="w-2 h-2 rounded-full bg-white animate-ping" />
            SOS
          </span>
        )
      case 'silent_sos':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-purple-600 text-white shadow-sm">
            <VolumeX className="w-3.5 h-3.5" />
            Silent SOS
          </span>
        )
      case 'panic_button':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-orange-600 text-white shadow-sm">
            <ShieldAlert className="w-3.5 h-3.5" />
            Panic Button
          </span>
        )
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-zinc-700 text-zinc-200">
            {type}
          </span>
        )
    }
  }

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-semibold bg-red-500/10 text-red-500 border border-red-500/30 animate-pulse">
            Pending Action
          </span>
        )
      case 'acknowledged':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">
            Acknowledged
          </span>
        )
      case 'verified':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            Verified
          </span>
        )
      case 'closed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-medium bg-zinc-800 text-zinc-400">
            Closed
          </span>
        )
      case 'cancelled':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-medium bg-zinc-800 text-zinc-500">
            Cancelled
          </span>
        )
      case 'false_alarm':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
            False Alarm
          </span>
        )
      default:
        return <span>{status}</span>
    }
  }

  const renderSlaTimer = (receivedAt: string, status: string, acknowledgedAt?: string) => {
    const start = new Date(receivedAt).getTime()
    const end = acknowledgedAt ? new Date(acknowledgedAt).getTime() : Date.now()
    const diffSec = Math.max(0, Math.floor((end - start) / 1000))
    const isOverdue = status === 'pending' && diffSec > 120

    return (
      <span
        className={`font-mono text-xs font-semibold ${
          isOverdue ? 'text-red-500 font-bold animate-pulse' : 'text-zinc-300'
        }`}
      >
        {Math.floor(diffSec / 60)}m {diffSec % 60}s {isOverdue ? '(SLA BREACH)' : ''}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Siren className="w-7 h-7 text-red-500" />
            SOS Emergency Alerts
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Parallel Emergency Intake • Direct GPS & Profile Transmissions • Urgent Human Verification
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
              soundEnabled
                ? 'bg-zinc-800 border-zinc-700 text-zinc-200'
                : 'bg-zinc-900 border-zinc-800 text-zinc-500'
            }`}
          >
            {soundEnabled ? <Volume2 className="w-4 h-4 text-emerald-400" /> : <VolumeX className="w-4 h-4" />}
            Sound Alerts
          </button>

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-200 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards (Dedicated SOS stats, NOT mixed into calls) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-[#181818] border-[#262626]">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Active SOS</p>
              <h3 className="text-2xl font-bold text-red-500 mt-1">{stats?.active_sos ?? 0}</h3>
              <p className="text-[11px] text-zinc-500 mt-0.5">Pending or in progress</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
              <Siren className="w-6 h-6 text-red-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#181818] border-[#262626]">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Silent SOS Today</p>
              <h3 className="text-2xl font-bold text-purple-400 mt-1">{stats?.silent_sos ?? 0}</h3>
              <p className="text-[11px] text-zinc-500 mt-0.5">Discreet panic triggers</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
              <VolumeX className="w-6 h-6 text-purple-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#181818] border-[#262626]">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Panic Button Today</p>
              <h3 className="text-2xl font-bold text-orange-400 mt-1">{stats?.panic_button ?? 0}</h3>
              <p className="text-[11px] text-zinc-500 mt-0.5">Rapid 3s hold activations</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center">
              <ShieldAlert className="w-6 h-6 text-orange-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#181818] border-[#262626]">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Avg Acknowledge SLA</p>
              <h3 className="text-2xl font-bold text-emerald-400 mt-1">
                {stats?.avg_time_to_acknowledge_seconds
                  ? `${stats.avg_time_to_acknowledge_seconds}s`
                  : 'N/A'}
              </h3>
              <p className="text-[11px] text-zinc-500 mt-0.5">Target &lt; 30 seconds</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Clock className="w-6 h-6 text-emerald-400" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-[#181818] p-3 rounded-xl border border-[#262626]">
        <div className="flex items-center gap-2 text-xs font-semibold text-zinc-400">
          <Filter className="w-4 h-4" /> Filters:
        </div>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="bg-[#222] border border-zinc-700 text-xs text-white rounded-lg px-3 py-1.5 focus:outline-none focus:border-red-500"
        >
          <option value="">All Alert Types</option>
          <option value="sos">SOS</option>
          <option value="silent_sos">Silent SOS</option>
          <option value="panic_button">Panic Button</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-[#222] border border-zinc-700 text-xs text-white rounded-lg px-3 py-1.5 focus:outline-none focus:border-red-500"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="verified">Verified</option>
          <option value="closed">Closed</option>
          <option value="cancelled">Cancelled</option>
          <option value="false_alarm">False Alarm</option>
        </select>

        {(statusFilter || typeFilter) && (
          <button
            onClick={() => {
              setStatusFilter('')
              setTypeFilter('')
            }}
            className="text-xs text-zinc-400 hover:text-white underline ml-2"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* SOS List Table */}
      <div className="bg-[#181818] border border-[#262626] rounded-xl overflow-hidden shadow-lg">
        {isLoading ? (
          <div className="p-12 text-center text-zinc-500">Loading alerts...</div>
        ) : alerts.length === 0 ? (
          <div className="p-12 text-center text-zinc-500">
            <CheckCircle className="w-8 h-8 mx-auto mb-2 text-emerald-500/50" />
            No active SOS alerts found matching current filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-zinc-300">
              <thead className="text-xs uppercase bg-[#202020] text-zinc-400 border-b border-[#2a2a2a]">
                <tr>
                  <th className="px-4 py-3">Time Received</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Citizen Name</th>
                  <th className="px-4 py-3">Contact</th>
                  <th className="px-4 py-3">Location Status</th>
                  <th className="px-4 py-3">Age of Alert</th>
                  <th className="px-4 py-3">SLA Timer</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#262626]">
                {alerts.map((alert: SOSListItem) => {
                  const isPending = alert.status === 'pending'
                  return (
                    <tr
                      key={alert.id}
                      onClick={() => navigate(`/sos/${alert.id}`)}
                      className={`hover:bg-[#202020] cursor-pointer transition-colors ${
                        isPending ? 'bg-red-500/5 font-medium' : ''
                      }`}
                    >
                      <td className="px-4 py-3.5 whitespace-nowrap text-xs">
                        {formatDateTime(alert.received_at)}
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">{renderTypeBadge(alert.alert_type)}</td>
                      <td className="px-4 py-3.5 whitespace-nowrap">{renderStatusBadge(alert.status)}</td>
                      <td className="px-4 py-3.5 whitespace-nowrap text-white font-medium">
                        {alert.user_name || 'Anonymous Citizen'}
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap text-xs">
                        {alert.user_phone ? (
                          <a
                            href={`tel:${alert.user_phone}`}
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-emerald-400 hover:underline"
                          >
                            <Phone className="w-3.5 h-3.5" />
                            {alert.user_phone}
                          </a>
                        ) : (
                          <span className="text-zinc-500">None provided</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap text-xs">
                        {alert.latitude && alert.longitude ? (
                          <span className="inline-flex items-center gap-1 text-emerald-400">
                            <MapPin className="w-3.5 h-3.5" />
                            GPS: ±{alert.accuracy_m ? Math.round(alert.accuracy_m) : '?'}m
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-amber-500/90">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            Location unavailable ({alert.location_status})
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap text-xs text-zinc-400">
                        {formatDistanceToNow(alert.received_at)}
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        {renderSlaTimer(alert.received_at, alert.status, alert.acknowledged_at)}
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            navigate(`/sos/${alert.id}`)
                          }}
                          className="inline-flex items-center gap-1 px-3 py-1 bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold text-white rounded-lg border border-zinc-700 transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          Respond
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
