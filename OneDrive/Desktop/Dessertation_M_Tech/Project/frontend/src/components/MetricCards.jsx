import React from 'react'

function MetricCard({ title, value, hint }) {
  return (
    <div className="p-4 card rounded-md flex flex-col">
      <div className="text-xs muted">{title}</div>
      <div className="text-2xl font-bold mt-2">{value}</div>
      {hint && <div className="text-xs muted mt-1">{hint}</div>}
    </div>
  )
}

export default function MetricCards({ metrics = [] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      {metrics.map((m) => (
        <MetricCard key={m.key} title={m.title} value={m.value} hint={m.hint} />
      ))}
    </div>
  )
}
