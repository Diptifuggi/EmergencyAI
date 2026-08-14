import React from 'react'

export default function IncidentWorkspace({ incident = null }) {
  if (!incident) return <div className="p-4 card rounded">Select an incident</div>

  return (
    <div className="card p-4 rounded">
      <h3 className="font-semibold">Incident {incident.id}</h3>
      <div className="muted">Related Calls: {incident.related_calls?.join(', ')}</div>
      <div className="mt-2">Similarity Score: {incident.score}</div>
      <div className="mt-3">Type: {incident.type}</div>
      <div className="mt-2">Priority: {incident.priority}</div>
    </div>
  )
}
