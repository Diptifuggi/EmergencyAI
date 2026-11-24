import React, { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAllEmergencies } from '@/api/emergencyApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import Card from '@/components/common/Card'
import { Bar, Doughnut, Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js'
import {
  buildCallMetrics,
  buildDailyCallSeries,
  localDateKey,
  safeChartData,
} from '@/lib/emergencyCallNormalizer'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Tooltip,
  Legend,
)

const formatCategory = (category: string) =>
  category.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

const dateInputValue = (date: Date) => localDateKey(date)

export default function Analytics() {
  const [period, setPeriod] = useState('7d')
  const now = new Date()
  const [customStart, setCustomStart] = useState(() => {
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6)
    return dateInputValue(start)
  })
  const [customEnd, setCustomEnd] = useState(() => dateInputValue(now))
  const { data: calls = [], isLoading, error } = useQuery({
    queryKey: ['emergency-calls', 'all'],
    queryFn: getAllEmergencies,
    refetchInterval: 30000,
    staleTime: 20000,
  })

  const dateRange = useMemo(() => {
    if (period === 'custom') {
      const start = new Date(`${customStart}T00:00:00`)
      const end = new Date(`${customEnd}T23:59:59.999`)
      return { start, end, valid: !Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime()) && start <= end }
    }
    const days = period === '1d' ? 1 : period === '30d' ? 30 : 7
    return {
      start: new Date(now.getFullYear(), now.getMonth(), now.getDate() - days + 1),
      end: new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999),
      valid: true,
    }
  }, [period, customStart, customEnd])

  const selectedCalls = useMemo(() => {
    if (!dateRange.valid) return []
    return calls.filter((call) => {
      if (!call.createdAt) return false
      const created = new Date(call.createdAt)
      return !Number.isNaN(created.getTime()) && created >= dateRange.start && created <= dateRange.end
    })
  }, [calls, dateRange])
  const metrics = useMemo(() => buildCallMetrics(selectedCalls, now), [selectedCalls])
  const dailyData = useMemo(() => {
    if (period !== 'custom' || !dateRange.valid) {
      const count = period === '1d' ? 1 : period === '30d' ? 30 : 7
      return buildDailyCallSeries(selectedCalls, count, now)
    }
    const days = Math.min(
      366,
      Math.floor((dateRange.end.getTime() - dateRange.start.getTime()) / 86400000) + 1,
    )
    const rangeCalls = selectedCalls.filter((call) => {
      const created = call.createdAt ? new Date(call.createdAt) : null
      return created && !Number.isNaN(created.getTime())
    })
    const counts = new Map<string, number>()
    const dates: Date[] = []
    for (let offset = 0; offset < days; offset += 1) {
      const date = new Date(dateRange.start.getFullYear(), dateRange.start.getMonth(), dateRange.start.getDate() + offset)
      const key = localDateKey(date)
      dates.push(date)
      counts.set(key, 0)
    }
    rangeCalls.forEach((call) => {
      const key = localDateKey(new Date(call.createdAt!))
      if (counts.has(key)) counts.set(key, counts.get(key)! + 1)
    })
    return {
      labels: dates.map((date) => date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })),
      data: dates.map((date) => counts.get(localDateKey(date)) ?? 0),
    }
  }, [period, selectedCalls, dateRange, now])
  const monthlyRows = useMemo(() => {
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    const previousDate = new Date(now.getFullYear(), now.getMonth() - 1, 1)
    const previousMonth = `${previousDate.getFullYear()}-${String(previousDate.getMonth() + 1).padStart(2, '0')}`
    const categories = new Map<string, { total: number; critical: number; high: number; scores: number[]; previous: number }>()
    calls.forEach((call) => {
      const created = call.createdAt ? new Date(call.createdAt) : null
      if (!created || Number.isNaN(created.getTime())) return
      const month = `${created.getFullYear()}-${String(created.getMonth() + 1).padStart(2, '0')}`
      if (month !== currentMonth && month !== previousMonth) return
      const category = call.category ?? 'Not reported'
      const row = categories.get(category) ?? { total: 0, critical: 0, high: 0, scores: [], previous: 0 }
      if (month === previousMonth) row.previous += 1
      if (month === currentMonth) {
        row.total += 1
        if (call.priority === 'Critical') row.critical += 1
        if (call.priority === 'High' || call.priority === 'Very High') row.high += 1
        if (call.priorityScore !== null) row.scores.push(call.priorityScore)
      }
      categories.set(category, row)
    })
    return [...categories.entries()].map(([category, row]) => ({
      category,
      ...row,
      average: row.scores.length
        ? row.scores.reduce((sum, score) => sum + score, 0) / row.scores.length
        : null,
      trend: row.total > row.previous ? 'up' : row.total < row.previous ? 'down' : 'same',
    })).sort((left, right) => left.category.localeCompare(right.category))
  }, [calls, now])

  if (isLoading) return <Loading />
  if (error) return <ErrorMessage error={error} />

  const categories = metrics.categories
  const categoryChartData = safeChartData(
    categories.map(([category]) => formatCategory(category)),
    categories.map(([, count]) => count),
    {
      backgroundColor: categories.map((_, index) => ['#111111', '#333333', '#555555', '#777777', '#999999'][index % 5]),
      borderRadius: 4,
      borderSkipped: false,
    },
  )
  const dailyChartData = safeChartData(dailyData.labels, dailyData.data, {
      borderColor: '#111111',
      backgroundColor: 'rgba(0,0,0,0.06)',
      borderWidth: 2,
      pointRadius: 3,
      pointBackgroundColor: '#111111',
      fill: true,
      tension: 0.3,
    })
  const priorityColors = ['#dc2626', '#f97316', '#f59e0b', '#16a34a', '#3b82f6']
  const priorityChartData = safeChartData(
    metrics.priorities.map((item) => item.level),
    metrics.priorities.map((item) => item.count),
    { backgroundColor: priorityColors },
  )
  const statusChartData = safeChartData(
    metrics.statuses.map(([status]) => status),
    metrics.statuses.map(([, count]) => count),
    { backgroundColor: ['#111111', '#555555', '#999999', '#d4d4d8', '#ef4444'] },
  )
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#888' } },
      y: { grid: { color: '#f4f4f4' }, ticks: { font: { size: 11 }, color: '#888' }, beginAtZero: true },
    },
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <div className="flex flex-wrap items-center gap-2">
          {[
            ['1d', 'Today'],
            ['7d', '7 Days'],
            ['30d', '30 Days'],
            ['custom', 'Custom'],
          ].map(([value, label]) => (
            <button
              key={value}
              onClick={() => setPeriod(value)}
              className={`rounded border px-3 py-1 text-sm ${period === value ? 'bg-zinc-900 text-white' : 'bg-white'}`}
            >
              {label}
            </button>
          ))}
          {period === 'custom' && (
            <>
              <label className="sr-only" htmlFor="analytics-start">Start date</label>
              <input id="analytics-start" aria-label="Start date" type="date" value={customStart} onChange={(event) => setCustomStart(event.target.value)} className="rounded border px-2 py-1 text-sm" />
              <label className="sr-only" htmlFor="analytics-end">End date</label>
              <input id="analytics-end" aria-label="End date" type="date" value={customEnd} onChange={(event) => setCustomEnd(event.target.value)} className="rounded border px-2 py-1 text-sm" />
            </>
          )}
        </div>
      </div>

      {!dateRange.valid ? (
        <div className="rounded border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">Choose a valid date range.</div>
      ) : (
        <>
          {calls.length === 0 && <div className="mb-4 rounded border border-zinc-200 bg-white p-4 text-sm text-zinc-600">No emergency calls are available for analytics.</div>}
          {calls.length > 0 && selectedCalls.length === 0 && <div className="mb-4 rounded border border-zinc-200 bg-white p-4 text-sm text-zinc-600">No calls were recorded in this period.</div>}
          <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card title="Calls per Category">
              <div className="relative" style={{ height: 260 }}>
                {categoryChartData.labels.length
                  ? <Bar data={categoryChartData} options={chartOptions} />
                  : <div className="flex h-full items-center justify-center text-sm text-zinc-500">No category data for this period.</div>}
              </div>
            </Card>
            <Card title="Daily Trends">
              <div className="relative" style={{ height: 260 }}>
                <Line data={dailyChartData} options={chartOptions} />
              </div>
            </Card>
          </div>

          <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card title="Priority Distribution">
              <div className="mb-2 text-sm text-zinc-500">Calls by persisted priority level</div>
              <div className="relative" style={{ height: 200 }}>
                <Bar data={priorityChartData} options={{ ...chartOptions, indexAxis: 'y' as const }} />
              </div>
            </Card>
            <Card title="Call Status">
              <div className="relative" style={{ height: 200 }}>
                {statusChartData.labels.length
                  ? <Doughnut data={statusChartData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' as const } } }} />
                  : <div className="flex h-full items-center justify-center text-sm text-zinc-500">No status data for this period.</div>}
              </div>
            </Card>
          </div>

          <Card title="Monthly Category Breakdown">
            {monthlyRows.length ? (
              <div className="overflow-x-auto">
                <table className="min-w-full border-collapse">
                  <thead><tr>
                    <th className="border-b px-4 py-3 text-left text-xs font-medium uppercase text-zinc-500">Category</th>
                    <th className="border-b px-4 py-3 text-left text-xs font-medium uppercase text-zinc-500">Total</th>
                    <th className="border-b px-4 py-3 text-left text-xs font-medium uppercase text-zinc-500">Critical</th>
                    <th className="border-b px-4 py-3 text-left text-xs font-medium uppercase text-zinc-500">High</th>
                    <th className="border-b px-4 py-3 text-left text-xs font-medium uppercase text-zinc-500">Avg Score</th>
                    <th className="border-b px-4 py-3 text-left text-xs font-medium uppercase text-zinc-500">Trend</th>
                  </tr></thead>
                  <tbody>{monthlyRows.map((row) => (
                    <tr key={row.category}>
                      <td className="border-b px-4 py-3 text-sm">{formatCategory(row.category)}</td>
                      <td className="border-b px-4 py-3 text-sm">{row.total}</td>
                      <td className="border-b px-4 py-3 text-sm">{row.critical}</td>
                      <td className="border-b px-4 py-3 text-sm">{row.high}</td>
                      <td className="border-b px-4 py-3 text-sm">{row.average == null ? 'Not reported' : row.average.toFixed(1)}</td>
                      <td className="border-b px-4 py-3 text-sm">{row.trend === 'same' ? '—' : row.trend === 'up' ? '↑' : '↓'}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            ) : <div className="text-sm text-zinc-500">No calls were recorded this month or last month.</div>}
          </Card>
        </>
      )}
    </div>
  )
}
