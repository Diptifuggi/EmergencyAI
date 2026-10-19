import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import {
  Phone,
  AlertTriangle,
  TrendingUp,
  CheckCircle,
  Zap,
  Activity,
  Clock,
  MapPin,
  ChevronRight,
} from 'lucide-react'
import { getEmergencyAnalytics } from '@/api/emergencyApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['emergency-analytics-summary'],
    queryFn: getEmergencyAnalytics,
    refetchInterval: 15000,
    staleTime: 10000,
  })

  if (isLoading) return <Loading />
  if (error) return <ErrorMessage error={error} />

  const formatMetric = (value: number | null | undefined) =>
    value == null ? '—' : value.toLocaleString()
  const levelStyles: Record<string, { background: string; foreground: string; dot: string; score: string }> = {
    Critical: { background: 'bg-red-100 text-red-800', foreground: 'bg-red-600', dot: 'bg-red-600', score: '#dc2626' },
    High: { background: 'bg-amber-100 text-amber-800', foreground: 'bg-amber-500', dot: 'bg-amber-500', score: '#f59e0b' },
    Moderate: { background: 'bg-green-100 text-green-800', foreground: 'bg-green-600', dot: 'bg-green-600', score: '#16a34a' },
    Low: { background: 'bg-blue-100 text-blue-800', foreground: 'bg-blue-500', dot: 'bg-blue-500', score: '#3b82f6' },
  }
  const maxSeverityCount = Math.max(1, ...data.severity_distribution.map((item: any) => item.count))
  const severityDistribution = data.severity_distribution.map((item: any) => ({
    ...item,
    color: levelStyles[item.level]?.score || '#71717a',
    width: `${(item.count / maxSeverityCount) * 100}%`,
  }))
  const recentCalls = data.recent_calls.map((call: any) => {
    const style = levelStyles[call.priority_level] || {
      background: 'bg-zinc-100 text-zinc-700',
      dot: 'bg-zinc-500',
      score: '#71717a',
    }
    const created = call.created_at ? new Date(call.created_at) : null
    const elapsedMinutes = created && !Number.isNaN(created.getTime())
      ? Math.max(0, Math.floor((Date.now() - created.getTime()) / 60000))
      : null
    return {
      ...call,
      caller_name: call.caller_name || 'Not available',
      caller_phone: call.caller_phone || 'Not available',
      time_ago: elapsedMinutes == null ? 'Not available' : elapsedMinutes < 1 ? 'Just now' : `${elapsedMinutes}m ago`,
      priority_level: call.priority_level || 'Not available',
      priority_color: style.background,
      dot_color: style.dot,
      score_color: style.score,
    }
  })

  const callRateData = {
    labels: data.call_rate_7days.labels,
    datasets: [
      {
        label: 'Calls',
        data: data.call_rate_7days.data,
        backgroundColor: '#1a1a1a',
        borderRadius: 3,
        borderSkipped: false,
      },
    ],
  }

  const callsCategoryData = {
    labels: Object.keys(data.calls_by_category),
    datasets: [
      {
        label: 'Calls',
        data: Object.values(data.calls_by_category),
        backgroundColor: ['#111111', '#333333', '#555555', '#777777', '#999999'],
        borderRadius: 3,
        borderSkipped: false,
      },
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#888' } },
      y: {
        grid: { color: '#f0f0f0' },
        ticks: { font: { size: 11 }, color: '#888' },
        beginAtZero: true,
      },
    },
  }

  return (
    <div className="space-y-6">
      {/* 8 Stat Cards — 4 columns, 2 rows */}
      <div className="grid grid-cols-4 gap-4">
        {/* Card 1: Total Calls */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-black rounded flex items-center justify-center">
              <Phone className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Total Calls</p>
          <p className="text-3xl font-semibold mb-2">{formatMetric(data.total_calls)}</p>
          <p className="text-green-600 text-xs">Records stored in PostgreSQL</p>
        </div>

        {/* Card 2: Critical */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-red-600 rounded flex items-center justify-center">
              <AlertTriangle className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Critical</p>
          <p className="text-3xl font-semibold mb-2">{formatMetric(data.critical_calls)}</p>
          <p className="text-red-600 text-xs">Based on backend priority analysis</p>
        </div>

        {/* Card 3: Today's Calls */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-black rounded flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Today's Calls</p>
          <p className="text-3xl font-semibold mb-2">{formatMetric(data.todays_calls)}</p>
          <p className="text-green-600 text-xs">Calls received today</p>
        </div>

        {/* Card 4: Resolved */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-green-600 rounded flex items-center justify-center">
              <CheckCircle className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Resolved</p>
          <p className="text-3xl font-semibold mb-2">{formatMetric(data.resolved)}</p>
          <p className="text-green-600 text-xs">Records with resolved status</p>
        </div>

        {/* Card 5: Dispatched */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-black rounded flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Dispatched</p>
          <p className="text-3xl font-semibold mb-2">{formatMetric(data.dispatched)}</p>
          <p className="text-red-600 text-xs">No persisted dispatch records available</p>
        </div>

        {/* Card 6: Avg Severity */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-amber-500 rounded flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Avg Severity</p>
          <p className="text-3xl font-semibold mb-2">{formatMetric(data.average_severity)}</p>
          <p className="text-zinc-500 text-xs">Mean of backend priority scores / 100</p>
        </div>

        {/* Card 7: Pending */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-black rounded flex items-center justify-center">
              <Clock className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Pending</p>
          <p className="text-3xl font-semibold mb-2">{formatMetric(data.pending)}</p>
          <p className="text-zinc-500 text-xs">Received or awaiting analysis</p>
        </div>

        {/* Card 8: Active Incidents */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-black rounded flex items-center justify-center">
              <MapPin className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Active Incidents</p>
          <p className="text-3xl font-semibold mb-2">{formatMetric(data.active_incidents)}</p>
          <p className="text-red-600 text-xs">No persisted incident records available</p>
        </div>
      </div>

      {/* 2 Charts — Side by side */}
      <div className="grid grid-cols-2 gap-4">
        {/* Chart 1: Call rate — last 7 days */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="mb-4">
            <h3 className="font-medium text-sm">Call rate — last 7 days</h3>
            <p className="text-xs text-zinc-500 mt-1">Daily incoming emergency calls</p>
          </div>
          <div style={{ height: '180px', position: 'relative' }}>
            <Bar data={callRateData} options={chartOptions} />
          </div>
        </div>

        {/* Chart 2: Calls by category */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="mb-4">
            <h3 className="font-medium text-sm">Calls by category</h3>
            <p className="text-xs text-zinc-500 mt-1">Top 5 emergency types</p>
          </div>
          <div style={{ height: '180px', position: 'relative' }}>
            <Bar data={callsCategoryData} options={chartOptions} />
          </div>
        </div>
      </div>

      {/* Recent Calls Table & Severity Distribution */}
      <div className="grid grid-cols-3 gap-4">
        {/* LEFT: Recent Critical Calls Table (flex-[3]) */}
        <div className="col-span-2 bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium text-sm">Recent critical calls</h3>
            <button className="text-xs border border-zinc-300 rounded px-2 py-1 hover:bg-zinc-50">
              View all <ChevronRight className="inline w-3 h-3" />
            </button>
          </div>
          <p className="text-xs text-zinc-500 mb-4">Last 5 high-priority emergency calls</p>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-zinc-200">
                <tr>
                  <th className="text-left py-2 px-2 text-xs font-medium text-zinc-500">Caller</th>
                  <th className="text-left py-2 px-2 text-xs font-medium text-zinc-500">Category</th>
                  <th className="text-left py-2 px-2 text-xs font-medium text-zinc-500">Priority</th>
                  <th className="text-left py-2 px-2 text-xs font-medium text-zinc-500">Score</th>
                  <th className="text-left py-2 px-2 text-xs font-medium text-zinc-500">Status</th>
                </tr>
              </thead>
              <tbody>
                {recentCalls.map((call: any) => (
                  <tr
                    key={call.id}
                    className={`border-b border-zinc-100 ${
                      call.priority_level === 'Critical'
                        ? 'border-l-2 border-l-red-600'
                        : call.priority_level === 'Very High'
                        ? 'border-l-2 border-l-orange-500'
                        : ''
                    }`}
                  >
                    <td className="py-2 px-2">
                      <div>
                        <div className="font-medium text-sm">{call.caller_name}</div>
                        <div className="text-xs text-zinc-500">{call.caller_phone}</div>
                      </div>
                    </td>
                    <td className="py-2 px-2 text-sm">{call.category}</td>
                    <td className="py-2 px-2">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${call.priority_color}`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${call.dot_color}`}></span>
                        {call.priority_level}
                      </span>
                    </td>
                    <td className="py-2 px-2">
                      <div>
                        <span className="text-sm font-medium">{formatMetric(call.final_score)}</span>
                        <div className="w-10 h-0.5 mt-1 rounded-full bg-zinc-200">
                          <div
                            className="h-0.5 rounded-full"
                            style={{
                              width: call.final_score == null ? '0%' : `${call.final_score}%`,
                              background: call.score_color,
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-2 px-2">
                      <span className="text-xs px-2 py-0.5 rounded bg-zinc-100 text-zinc-600">
                        {call.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* RIGHT: Severity Distribution (flex-[2]) */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <h3 className="font-medium text-sm mb-1">Severity distribution</h3>
          <p className="text-xs text-zinc-500 mb-4">Calls by priority level</p>

          <div className="space-y-3 mb-4">
            {severityDistribution.map((item: any) => (
              <div key={item.level} className="flex items-center gap-2">
                <span className="text-xs text-zinc-500 w-16">{item.level}</span>
                <div className="flex-1 h-2 bg-zinc-100 rounded-full">
                  <div
                    className="h-2 rounded-full"
                    style={{ width: item.width, background: item.color }}
                  />
                </div>
                <span className="text-xs font-medium text-zinc-700 w-6 text-right">
                  {item.count}
                </span>
              </div>
            ))}
          </div>

          <div className="border-t border-zinc-200 pt-3 mt-3">
            <p className="text-xs text-zinc-500 mb-2">Emergency channels</p>
            <div className="grid grid-cols-2 gap-2">
              {data.channels.length > 0 ? data.channels.slice(0, 4).map((channel: any) => (
                <div key={channel.source} className="bg-zinc-50 rounded-md p-2">
                  <div className="text-xs text-zinc-500">{channel.source}</div>
                  <div className="text-base font-semibold">{channel.count} calls</div>
                </div>
              )) : (
                <div className="bg-zinc-50 rounded-md p-2">
                  <div className="text-xs text-zinc-500">Not available</div>
                  <div className="text-base font-semibold">No call sources</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
