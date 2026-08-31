import React from 'react'

export default function IncidentCorrelationPanel({ clusters = [] }) {
  return (
    <div className="card rounded-md p-4">
      <h3 className="font-semibold">Incident Correlation</h3>
      <div className="mt-3 space-y-3">
        {clusters.length === 0 && <div className="muted">No correlated incidents</div>}
        {clusters.map((c) => (
          <div key={c.id} className="p-3 border rounded" style={{ borderColor: 'var(--border)' }}>
            <div className="flex justify-between">
              <div className="font-medium">Incident {c.id}</div>
              <div className="muted">Score {c.score}</div>
            </div>
            <div className="text-xs muted mt-1">Related Calls: {c.related_calls.join(', ')}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
