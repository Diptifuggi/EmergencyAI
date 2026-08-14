import React from 'react'
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

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const MOCK = {
  total_calls: 1284,
  critical_calls: 18,
  dispatched: 65,
  resolved: 931,
  average_severity: 61.4,
  todays_calls: 47,
  pending: 24,
  active_incidents: 12,
  calls_by_status: {
    Pending: 24,
    Processing: 18,
    Assigned: 12,
    Resolved: 931,
  },
  calls_by_category: {
    'Road Accident': 38,
    'Medical Emergency': 29,
    'Fire': 18,
    'Women Safety': 12,
    'Other': 9,
  },
  call_rate_7days: {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    data: [28, 35, 41, 30, 47, 22, 18],
  },
  severity_distribution: [
    { level: 'Critical', count: 18, color: '#dc2626', width: '18%' },
    { level: 'Very High', count: 32, color: '#f97316', width: '32%' },
    { level: 'High', count: 49, color: '#f59e0b', width: '49%' },
    { level: 'Moderate', count: 71, color: '#16a34a', width: '71%' },
    { level: 'Low', count: 100, color: '#3b82f6', width: '100%' },
  ],
  recent_calls: [
    {
      id: 'mock-001',
      caller_name: 'Ramesh P.',
      caller_phone: '+91 98765 43210',
      time_ago: '12m ago',
      category: 'Road Accident',
      priority_level: 'Critical',
      priority_color: 'bg-red-100 text-red-800',
      dot_color: 'bg-red-600',
      final_score: 92.4,
      score_color: '#dc2626',
      status: 'Processing',
    },
    {
      id: 'mock-002',
      caller_name: 'Priya S.',
      caller_phone: '+91 87654 32109',
      time_ago: '28m ago',
      category: 'Medical Emergency',
      priority_level: 'Very High',
      priority_color: 'bg-orange-100 text-orange-800',
      dot_color: 'bg-orange-500',
      final_score: 78.1,
      score_color: '#f97316',
      status: 'Assigned',
    },
    {
      id: 'mock-003',
      caller_name: 'Ankit M.',
      caller_phone: '+91 76543 21098',
      time_ago: '45m ago',
      category: 'Fire',
      priority_level: 'High',
      priority_color: 'bg-amber-100 text-amber-800',
      dot_color: 'bg-amber-500',
      final_score: 65.7,
      score_color: '#f59e0b',
      status: 'Pending',
    },
    {
      id: 'mock-004',
      caller_name: 'Sunita K.',
      caller_phone: '+91 65432 10987',
      time_ago: '1h ago',
      category: 'Women Safety',
      priority_level: 'High',
      priority_color: 'bg-amber-100 text-amber-800',
      dot_color: 'bg-amber-500',
      final_score: 59.2,
      score_color: '#f59e0b',
      status: 'Processing',
    },
    {
      id: 'mock-005',
      caller_name: 'Vijay R.',
      caller_phone: '+91 54321 09876',
      time_ago: '1h 33m ago',
      category: 'Natural Disaster',
      priority_level: 'Moderate',
      priority_color: 'bg-green-100 text-green-800',
      dot_color: 'bg-green-600',
      final_score: 38.5,
      score_color: '#16a34a',
      status: 'Resolved',
    },
  ],
}

export default function Dashboard() {
  const data: any = MOCK
  const isLoading = false

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
          <p className="text-3xl font-semibold mb-2">{data.total_calls.toLocaleString()}</p>
          <p className="text-green-600 text-xs">↑ 3.4% since last month</p>
        </div>

        {/* Card 2: Critical */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-red-600 rounded flex items-center justify-center">
              <AlertTriangle className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Critical</p>
          <p className="text-3xl font-semibold mb-2">{data.critical_calls}</p>
          <p className="text-red-600 text-xs">↑ 5 since last week</p>
        </div>

        {/* Card 3: Today's Calls */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-black rounded flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Today's Calls</p>
          <p className="text-3xl font-semibold mb-2">{data.todays_calls}</p>
          <p className="text-green-600 text-xs">↑ 1.2% since yesterday</p>
        </div>

        {/* Card 4: Resolved */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-green-600 rounded flex items-center justify-center">
              <CheckCircle className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Resolved</p>
          <p className="text-3xl font-semibold mb-2">{data.resolved.toLocaleString()}</p>
          <p className="text-green-600 text-xs">↑ 7.1% since last month</p>
        </div>

        {/* Card 5: Dispatched */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-black rounded flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Dispatched</p>
          <p className="text-3xl font-semibold mb-2">{data.dispatched}</p>
          <p className="text-red-600 text-xs">↓ 1.0% since last week</p>
        </div>

        {/* Card 6: Avg Severity */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-amber-500 rounded flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Avg Severity</p>
          <p className="text-3xl font-semibold mb-2">{data.average_severity}</p>
          <p className="text-zinc-500 text-xs">/100 score</p>
        </div>

        {/* Card 7: Pending */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-black rounded flex items-center justify-center">
              <Clock className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Pending</p>
          <p className="text-3xl font-semibold mb-2">{data.pending}</p>
          <p className="text-zinc-500 text-xs">Awaiting triage</p>
        </div>

        {/* Card 8: Active Incidents */}
        <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 bg-black rounded flex items-center justify-center">
              <MapPin className="w-4 h-4 text-white" />
            </div>
          </div>
          <p className="text-xs text-zinc-500 uppercase mb-1">Active Incidents</p>
          <p className="text-3xl font-semibold mb-2">{data.active_incidents}</p>
          <p className="text-red-600 text-xs">↓ 3 since yesterday</p>
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
                {data.recent_calls.map((call: any) => (
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
                        <span className="text-sm font-medium">{call.final_score}</span>
                        <div className="w-10 h-0.5 mt-1 rounded-full bg-zinc-200">
                          <div
                            className="h-0.5 rounded-full"
                            style={{
                              width: `${call.final_score}%`,
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
            {data.severity_distribution.map((item: any) => (
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
              <div className="bg-zinc-50 rounded-md p-2">
                <div className="text-xs text-zinc-500">112</div>
                <div className="text-base font-semibold">Police</div>
              </div>
              <div className="bg-zinc-50 rounded-md p-2">
                <div className="text-xs text-zinc-500">100</div>
                <div className="text-base font-semibold">Fire</div>
              </div>
              <div className="bg-zinc-50 rounded-md p-2">
                <div className="text-xs text-zinc-500">108</div>
                <div className="text-base font-semibold">Ambulance</div>
              </div>
              <div className="bg-zinc-50 rounded-md p-2">
                <div className="text-xs text-zinc-500">101</div>
                <div className="text-base font-semibold">Disaster</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
