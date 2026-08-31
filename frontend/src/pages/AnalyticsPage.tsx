// @ts-nocheck
import React, { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import dashboardApi from '@/api/dashboardApi'
import { Bar, Doughnut } from 'react-chartjs-2'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend } from 'chart.js'
import { Card, CardHeader, CardTitle, CardContent, Button, Badge } from '@/components/ui'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend)

export default function AnalyticsPage() {
  const [period, setPeriod] = useState('7d')
  const { data, isLoading, error } = useQuery({ queryKey: ['analytics', period], queryFn: dashboardApi.getSummary })

  const callVolumeData = useMemo(() => {
    const labels = data?.call_rate?.labels || []
    const values = data?.call_rate?.values || []
    return {
      labels,
      datasets: [
        {
          label: 'Calls',
          data: values,
          backgroundColor: '#1a1a1a',
        }
      ]
    }
  }, [data])

  const callVolumeOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { maxRotation: 0, autoSkip: true } },
    }
  }), [])

  const doughnutData = useMemo(() => {
    const labels = (data?.calls_by_category_top5 || []).map(c => c.name)
    const counts = labels.map((l, i) => (i + 1) * 10)
    const bg = ['#f3f4f6','#e5e7eb','#d1d5db','#9ca3af','#6b7280']
    return { labels, datasets: [{ data: counts, backgroundColor: bg }] }
  }, [data])

  const priorityData = useMemo(() => {
    const dist = data?.severity_distribution || {}
    const labels = ['Critical','Very High','High','Moderate','Low']
    const colors = ['#dc2626','#f97316','#f59e0b','#10b981','#3b82f6']
    const vals = labels.map(l => dist[l] || 0)
    return { labels, datasets: [{ data: vals, backgroundColor: colors }] }
  }, [data])

  const statusDoughnut = useMemo(() => {
    const obj = data?.calls_by_status || {}
    const labels = Object.keys(obj)
    const vals = labels.map(k => obj[k])
    const shades = ['#f3f4f6','#e5e7eb','#d1d5db','#9ca3af']
    return { labels, datasets: [{ data: vals, backgroundColor: shades }] }
  }, [data])

  const tableRows = useMemo(() => {
    const cats = ['Road Accident','Medical Emergency','Fire','Women Safety','Other']
    return cats.map(cat => ({
      category: cat,
      total: Math.floor(Math.random()*100)+20,
      critical: Math.floor(Math.random()*10),
      high: Math.floor(Math.random()*20),
      avgScore: (Math.random()*50+50).toFixed(1),
      trendUp: Math.random() > 0.5
    }))
  }, [data])

  if (isLoading) return <div className="p-6">Loading...</div>
  if (error) return <div className="p-6 text-red-600">Failed to load analytics</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Analytics & Reports</h1>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-white border rounded p-1">
            {['Today','7 Days','30 Days','Custom'].map(p => (
              <button key={p} onClick={()=>setPeriod(p==='Today'? '1d': p==='7 Days'? '7d' : p==='30 Days'? '30d':'custom')} className={`px-3 py-1 rounded ${period=== (p==='Today'? '1d': p==='7 Days'? '7d' : p==='30 Days'? '30d':'custom') ? 'bg-black text-white' : ''}`}>{p}</button>
            ))}
          </div>
          <Button onClick={()=>{ const csv = JSON.stringify(data); const blob = new Blob([csv], { type: 'text/csv' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'analytics.json'; a.click(); URL.revokeObjectURL(url); }}>Export</Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Call Volume Trend</CardTitle>
            </CardHeader>
            <CardContent style={{height:220}}>
              <Bar data={callVolumeData} options={callVolumeOptions} />
            </CardContent>
          </Card>
        </div>
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Call Distribution</CardTitle>
            </CardHeader>
            <CardContent style={{height:220}}>
              <div className="h-40">
                <Doughnut data={doughnutData} options={{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}}} />
              </div>
              <div className="mt-3">
                {(doughnutData.labels || []).map((lbl,i)=> (
                  <div key={lbl} className="flex items-center justify-between text-sm">
                    <div>{lbl}</div>
                    <div className="text-gray-600">{doughnutData.datasets[0].data[i]} ({Math.round((doughnutData.datasets[0].data[i]/(doughnutData.datasets[0].data.reduce((a,b)=>a+b,0)||1))*100)}%)</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader><CardTitle>Category Breakdown (6 months)</CardTitle></CardHeader>
          <CardContent style={{height:200}}>
            <div className="text-sm text-gray-600">Stacked bar sample visualization</div>
            <div className="h-36 mt-2 bg-gray-50 flex items-center justify-center text-sm text-gray-500">Stacked bar chart placeholder (render with Chart.js if desired)</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Priority Distribution</CardTitle></CardHeader>
          <CardContent style={{height:200}}>
            <div className="h-36">
              <Bar data={priorityData} options={{ indexAxis: 'y', responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}} }} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Response Ratio</CardTitle></CardHeader>
          <CardContent style={{height:200}}>
            <div className="h-36">
              <Doughnut data={statusDoughnut} options={{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}} }} />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Monthly Category Breakdown</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left"><th>Category</th><th>Total</th><th>Critical</th><th>High</th><th>Avg Score</th><th>Trend</th></tr>
            </thead>
            <tbody>
              {tableRows.map(row => (
                <tr key={row.category} className="border-t"><td>{row.category}</td><td>{row.total}</td><td>{row.critical}</td><td>{row.high}</td><td>{row.avgScore}</td><td>{row.trendUp ? <span className="text-green-600">↑</span> : <span className="text-red-600">↓</span>}</td></tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}
