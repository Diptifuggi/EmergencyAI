import React from 'react'

function AgencyRow({ name, status, count }) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="font-medium">{name}</div>
      <div className="muted">{status} • {count}</div>
    </div>
  )
}

export default function DispatchPanel({ agencies = [] }) {
  return (
    <div className="card p-4 rounded-md">
      <h3 className="font-semibold">Dispatch Status</h3>
      <div className="mt-3">
        {agencies.map((a) => <AgencyRow key={a.name} {...a} />)}
      </div>
    </div>
  )
}
