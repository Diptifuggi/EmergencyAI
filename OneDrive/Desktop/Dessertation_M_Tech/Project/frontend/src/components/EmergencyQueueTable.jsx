import React from 'react'

export default function EmergencyQueueTable({ data = [] }) {
  return (
    <div className="card rounded-md overflow-auto">
      <table className="min-w-full text-sm table-auto">
        <thead>
          <tr className="text-left">
            <th className="p-3">Call ID</th>
            <th className="p-3">Time</th>
            <th className="p-3">Category</th>
            <th className="p-3">Severity</th>
            <th className="p-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {data.length === 0 && (
            <tr>
              <td colSpan="5" className="p-6 muted text-center">No active calls</td>
            </tr>
          )}
          {data.map((row) => (
            <tr key={row.id} className="border-t" style={{ borderColor: 'var(--border)' }}>
              <td className="p-3">{row.id}</td>
              <td className="p-3">{row.time}</td>
              <td className="p-3 muted">{row.category}</td>
              <td className="p-3">{row.severity}</td>
              <td className="p-3 muted">{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
