// @ts-nocheck
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAnalytics } from '@/api/analyticsApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import Card from '@/components/common/Card'
import { Bar, Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend)

export default function Analytics() {
  const MOCK_ANALYTICS = {
    calls_per_category: {
      labels: ['Road Accident', 'Medical', 'Fire', 'Women Safety', 'Child Abuse', 'Cyber Crime', 'Natural Disaster', 'Other'],
      data: [38, 29, 18, 12, 8, 6, 11, 5],
    },
    daily_trends: {
      labels: ['Jun 20', 'Jun 21', 'Jun 22', 'Jun 23', 'Jun 24', 'Jun 25', 'Jun 26'],
      data: [32, 28, 45, 38, 52, 41, 47],
    },
    priority_distribution: {
      labels: ['Critical', 'Very High', 'High', 'Moderate', 'Low'],
      data: [18, 32, 49, 71, 100],
      colors: ['#dc2626', '#f97316', '#f59e0b', '#16a34a', '#3b82f6'],
    },
    monthly_summary: {
      labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
      datasets: [
        { label: 'Road Accident', data: [22, 19, 28, 31, 25, 38], color: '#111111' },
        { label: 'Medical', data: [18, 21, 24, 19, 27, 29], color: '#444444' },
        { label: 'Fire', data: [8, 11, 9, 14, 12, 18], color: '#777777' },
        { label: 'Other', data: [12, 9, 15, 11, 18, 14], color: '#aaaaaa' },
      ],
    },
  }

  // TODO: Replace with real API when backend is ready
  // const { data, isLoading, error } = useQuery({ queryKey: ['analytics'], queryFn: getAnalytics })
  void useQuery
  const analyticsData = MOCK_ANALYTICS
  const isLoading = false
  const error = null

  const categoryChartData = {
    labels: analyticsData.calls_per_category.labels,
    datasets: [
      {
        label: 'Calls',
        data: analyticsData.calls_per_category.data,
        backgroundColor: '#1a1a1a',
        borderRadius: 4,
        borderSkipped: false,
      },
    ],
  }

  const categoryChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#888' } },
      y: { grid: { color: '#f4f4f4' }, ticks: { font: { size: 11 }, color: '#888' }, beginAtZero: true },
    },
  }

  const dailyChartData = {
    labels: analyticsData.daily_trends.labels,
    datasets: [
      {
        label: 'Calls',
        data: analyticsData.daily_trends.data,
        borderColor: '#111111',
        backgroundColor: 'rgba(0,0,0,0.06)',
        borderWidth: 2,
        pointRadius: 4,
        pointBackgroundColor: '#111111',
        fill: true,
        tension: 0.3,
      },
    ],
  }

  const dailyChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#888' } },
      y: { grid: { color: '#f4f4f4' }, ticks: { font: { size: 11 }, color: '#888' }, beginAtZero: true },
    },
  }

  const priorityChartData = {
    labels: analyticsData.priority_distribution.labels,
    datasets: [
      {
        label: 'Calls',
        data: analyticsData.priority_distribution.data,
        backgroundColor: analyticsData.priority_distribution.colors,
      },
    ],
  }

  const priorityChartOptions = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: '#f4f4f4' }, ticks: { font: { size: 11 }, color: '#888' }, beginAtZero: true },
      y: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#888' } },
    },
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Analytics</h1>
      {isLoading ? (
        <Loading />
      ) : error ? (
        <ErrorMessage error={error} />
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
            <Card title="Calls per Category">
              <div style={{ height: '260px', position: 'relative' }}>
                <Bar data={categoryChartData} options={categoryChartOptions} />
              </div>
            </Card>
            <Card title="Daily Trends">
              <div style={{ height: '260px', position: 'relative' }}>
                <Line data={dailyChartData} options={dailyChartOptions} />
              </div>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card title="Priority Distribution">
              <div className="mb-2 text-sm text-zinc-500">Calls by severity level</div>
              <div style={{ height: '200px', position: 'relative' }}>
                <Bar data={priorityChartData} options={priorityChartOptions} />
              </div>
            </Card>

            <Card title="Monthly Category Breakdown">
              <div className="overflow-x-auto">
                <table className="min-w-full border-collapse">
                  <thead>
                    <tr>
                      <th className="text-xs font-medium text-zinc-500 uppercase px-4 py-3 border-b">Category</th>
                      {analyticsData.monthly_summary.labels.map((month) => (
                        <th key={month} className="text-xs font-medium text-zinc-500 uppercase px-4 py-3 border-b">{month}</th>
                      ))}
                      <th className="text-xs font-medium text-zinc-500 uppercase px-4 py-3 border-b">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analyticsData.monthly_summary.datasets.map((set, index) => {
                      const total = set.data.reduce((sum, value) => sum + value, 0)
                      return (
                        <tr key={set.label} className={index % 2 === 1 ? 'bg-zinc-50' : ''}>
                          <td className="text-sm font-medium text-zinc-800 px-4 py-3 border-b">{set.label}</td>
                          {set.data.map((value, monthIndex) => (
                            <td key={monthIndex} className="text-sm px-4 py-3 border-b border-zinc-100">{value}</td>
                          ))}
                          <td className="text-sm px-4 py-3 border-b border-zinc-100">{total}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
