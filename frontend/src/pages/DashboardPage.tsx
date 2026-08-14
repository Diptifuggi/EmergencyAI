import React, { useMemo, useId } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Tooltip,
  Legend,
  Title,
  PointElement,
  LineElement,
  type ChartOptions,
} from 'chart.js'
import { Bar, Doughnut } from 'react-chartjs-2'
import {
  Phone,
  AlertTriangle,
  TrendingUp,
  CheckCircle2,
  Zap,
  Activity,
  Clock,
  MapPin,
  RefreshCw,
  Eye,
} from 'lucide-react'

import StatCard from '@/components/ui/StatCard'
import { PriorityBadge, StatusBadge } from '@/components/ui'
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Button,
  Skeleton,
} from '@/components/ui'

import dashboardApi from '@/api/dashboardApi'
import formatters from '@/lib/formatters'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend, Title, PointElement, LineElement)

const CHART_HEIGHT = 180

const callRateOptions: ChartOptions<'bar'> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { display: false } },
    y: { beginAtZero: true },
  },
}

const stackedOptions: ChartOptions<'bar'> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: { x: { stacked: true }, y: { stacked: true } },
}

const doughnutOptions: ChartOptions<'doughnut'> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const id = useId()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: dashboardApi.getSummary,
    refetchInterval: 30000,
  })

  const lastUpdated = useMemo(() => {
    const ts = data?.updated_at ? new Date(data.updated_at) : new Date()
    return format(ts, 'PPpp')
  }, [data])

  const stats = useMemo(() => {
    const d: any = data || {}
    return [
      { label: 'Total Calls', value: formatters.number(d.total_calls || 0), icon: <Phone className="w-4 h-4 text-gray-700" />, iconBg: 'bg-gray-100', delta: d.total_calls_delta || 0, deltaDirection: d.total_calls_delta >= 0 ? 'up' : 'down' },
      { label: 'Critical', value: formatters.number(d.critical_calls || 0), icon: <AlertTriangle className="w-4 h-4 text-yellow-700" />, iconBg: 'bg-yellow-100', delta: d.critical_calls_delta || 0, deltaDirection: d.critical_calls_delta >= 0 ? 'up' : 'down' },
      { label: "Today's Calls", value: formatters.number(d.todays_calls || 0), icon: <TrendingUp className="w-4 h-4 text-gray-700" />, iconBg: 'bg-gray-100', delta: d.todays_calls_delta || 0, deltaDirection: d.todays_calls_delta >= 0 ? 'up' : 'down' },
      { label: 'Resolved', value: formatters.number((d.calls_by_status?.Resolved) || 0), icon: <CheckCircle2 className="w-4 h-4 text-green-700" />, iconBg: 'bg-green-100', delta: d.resolved_delta || 0, deltaDirection: d.resolved_delta >= 0 ? 'up' : 'down' },
      { label: 'Dispatched', value: formatters.number(d.active_incidents || 0), icon: <Zap className="w-4 h-4 text-indigo-700" />, iconBg: 'bg-indigo-100', delta: d.dispatched_delta || 0, deltaDirection: d.dispatched_delta >= 0 ? 'up' : 'down' },
      { label: 'Avg Severity', value: `${((d.average_severity || 0) / 100).toFixed(1)}/100`, icon: <Activity className="w-4 h-4 text-purple-700" />, iconBg: 'bg-purple-100', delta: d.average_severity_delta || 0, deltaDirection: d.average_severity_delta >= 0 ? 'up' : 'down' },
      { label: 'Pending', value: formatters.number(d.calls_by_status?.Pending || 0), icon: <Clock className="w-4 h-4 text-gray-700" />, iconBg: 'bg-gray-100', delta: d.pending_delta || 0, deltaDirection: d.pending_delta >= 0 ? 'up' : 'down' },
      { label: 'Active Incidents', value: formatters.number(d.active_incidents || 0), icon: <MapPin className="w-4 h-4 text-red-700" />, iconBg: 'bg-red-100', delta: d.active_incidents_delta || 0, deltaDirection: d.active_incidents_delta >= 0 ? 'up' : 'down' },
    ]
  }, [data])

  const callRateData = useMemo(() => {
    const days = (data?.call_rate?.labels && data.call_rate.labels.length) ? data.call_rate.labels : (() => {
      const arr: string[] = []
      for (let i = 13; i >= 0; i--) {
        const d = new Date()
        d.setDate(d.getDate() - i)
        arr.push(format(d, 'MMM d'))
      }
      return arr
    })()

    const values = data?.call_rate?.values || new Array(days.length).fill(0)

    return {
      labels: days,
      datasets: [
        {
          label: 'Call Rate',
          data: values,
          backgroundColor: '#111',
        },
      ],
    }
  }, [data])

  const eventStatusData = useMemo(() => {
    const counts: any = data?.event_status || {}
    const pending = counts.Pending || 0
    const processing = counts.Processing || 0
    const assigned = counts.Assigned || 0
    const resolved = counts.Resolved || 0
    const total = pending + processing + assigned + resolved || 1
    return {
      datasets: [
        {
          data: [pending, processing, assigned, resolved],
          backgroundColor: ['#000', '#555', '#999', '#ddd'],
        },
      ],
      labels: ['Pending', 'Processing', 'Assigned', 'Resolved'],
      meta: { total },
    }
  }, [data])

  const categoryStackedData = useMemo(() => {
    const categories = data?.calls_by_category_top5 || []
    const states = data?.state_breakdown || []

    const labels = categories.map((c: any) => c.name)
    const colors = ['#111', '#333', '#555', '#777', '#aaa']

    const datasets = (categories || []).map((cat: any, idx: number) => ({
      label: cat.name,
      data: states.map((s: any) => (s.counts?.[cat.name] || 0)),
      backgroundColor: colors[idx % colors.length],
    }))

    return { labels: states.map((s: any) => s.state || 'Unknown'), datasets }
  }, [data])

  const severityData = useMemo(() => {
    const s: any = data?.severity_distribution || { Critical: 0, 'Very High': 0, High: 0, Moderate: 0, Low: 0 }
    const labels = ['Critical', 'Very High', 'High', 'Moderate', 'Low']
    const colors = ['#dc2626', '#f97316', '#f59e0b', '#16a34a', '#3b82f6']
    return {
      labels,
      datasets: [
        {
          label: 'Severity',
          data: labels.map((l) => s[l] || 0),
          backgroundColor: colors,
        },
      ],
    }
  }, [data])

  const recent = data?.recent_critical_calls || []

  const callTypeRatio = useMemo(() => {
    const ratio: any = data?.call_type_ratio || { voice: 0, sms: 0, other: 0 }
    const labels = Object.keys(ratio)
    const values = labels.map((k) => ratio[k])
    const colors = ['#111', '#555', '#999']
    return { labels, datasets: [{ data: values, backgroundColor: colors }] }
  }, [data])

  const onView = (id: string) => navigate(`/calls/${id}`)

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Operations Dashboard</h1>
          <div className="text-sm text-gray-500">National Emergency Response Center · 112 / 100 / 101 / 108</div>
        </div>

        <div className="flex items-center space-x-4 text-sm text-gray-600">
          <div className="text-right">
            <div className="text-xs text-gray-500">Last Updated:</div>
            <div className="font-medium">{lastUpdated}</div>
          </div>
          <Button onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
        </div>
      </div>

      {/* Stat grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {isLoading
          ? new Array(8).fill(0).map((_, i) => (
              <div key={i} className="w-full">
                <Skeleton className="h-20 w-full rounded-lg" />
              </div>
            ))
          : stats.map((s: any, idx: number) => (
              <StatCard key={idx} icon={s.icon} iconBg={s.iconBg} label={s.label} value={s.value} delta={s.delta} deltaDirection={s.deltaDirection} />
            ))}
      </div>

      {/* Row 1 charts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="md:col-span-2 bg-white rounded-lg p-4 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-medium">Call Rate — Last 14 Days</h3>
          </div>
          <div style={{ height: CHART_HEIGHT }}>
            {isLoading ? <Skeleton className="h-full w-full" /> : <Bar data={callRateData} options={callRateOptions} />}
          </div>
        </div>

        <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-medium">Event Status</h3>
          </div>
          <div style={{ height: CHART_HEIGHT }} className="flex flex-col md:flex-row items-center">
            <div className="w-36 h-36">
              {isLoading ? <Skeleton className="w-36 h-36 rounded-full" /> : <Doughnut data={eventStatusData} options={doughnutOptions} />}
            </div>
            <div className="ml-4 flex-1">
              {!isLoading && (
                <div>
                  <div className="text-sm text-gray-500">Total Count</div>
                  <div className="text-2xl font-semibold">{eventStatusData.meta.total}</div>

                  <div className="mt-4 space-y-2">
                    {eventStatusData.labels.map((label: any, i: number) => {
                      const count = eventStatusData.datasets[0].data[i] || 0
                      const pct = ((count / eventStatusData.meta.total) * 100).toFixed(1)
                      const color = eventStatusData.datasets[0].backgroundColor[i]
                      return (
                        <div key={label} className="flex items-center justify-between">
                          <div className="flex items-center">
                            <span className="w-3 h-3 mr-2 rounded-full" style={{ backgroundColor: color }} />
                            <div className="text-sm">{label}</div>
                          </div>
                          <div className="text-sm text-gray-600">{count} • {pct}%</div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Row 2 charts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="md:col-span-2 bg-white rounded-lg p-4 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-medium">Calls by Category — State Breakdown</h3>
          </div>
          <div style={{ height: CHART_HEIGHT }}>
            {isLoading ? <Skeleton className="h-full w-full" /> : <Bar data={categoryStackedData} options={stackedOptions} />}
          </div>
        </div>

        <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-medium">Severity Distribution</h3>
          </div>
          <div style={{ height: CHART_HEIGHT }}>
            {isLoading ? <Skeleton className="h-full w-full" /> : <Doughnut data={severityData} options={doughnutOptions} />}
          </div>
        </div>
      </div>

      {/* Row 3: Call Type Ratio + Recent Calls */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 bg-white rounded-lg p-4 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-medium">Call Type Ratio</h3>
          </div>
          <div className="flex flex-col lg:flex-row items-center gap-6">
            <div className="w-44 h-44">
              {isLoading ? <Skeleton className="w-full h-full rounded-full" /> : <Doughnut data={callTypeRatio} options={doughnutOptions} />}
            </div>
            <div className="flex-1 space-y-2 w-full">
              {callTypeRatio.labels.map((label: any, idx: number) => (
                <div key={label} className="flex items-center justify-between rounded-xl border border-gray-100 bg-gray-50 px-4 py-3">
                  <div className="flex items-center gap-3">
                    <span className="block h-3 w-3 rounded-full" style={{ backgroundColor: callTypeRatio.datasets[0].backgroundColor[idx] }} />
                    <span className="text-sm font-medium">{label}</span>
                  </div>
                  <span className="text-sm text-gray-600">{callTypeRatio.datasets[0].data[idx]}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-medium">Recent Critical Calls</h3>
            <Button onClick={() => refetch()}>Refresh</Button>
          </div>
          <div className="space-y-3">
            {(recent || []).slice(0, 5).map((call: any) => (
              <div key={call.id} className="rounded-xl border border-gray-100 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-semibold text-slate-900">{call.caller_name}</div>
                    <div className="text-sm text-gray-500">{call.category} • {call.time_ago}</div>
                  </div>
                  <div className="text-sm font-semibold text-slate-700">{call.status}</div>
                </div>
                <div className="mt-3 flex items-center justify-between text-sm text-gray-500">
                  <span>{call.caller_phone}</span>
                  <button type="button" onClick={() => onView(call.id)} className="text-sky-600 hover:underline">View</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
