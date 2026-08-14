import React from 'react'

export default function CallDetailsWorkspace({ call = null }) {
  if (!call) return <div className="p-4 card rounded">Select a call to view details</div>

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="card p-4 rounded"> 
        <h4 className="font-semibold">Call Queue</h4>
        <div className="muted mt-2">Position: {call.queue_position}</div>
      </div>

      <div className="card p-4 rounded">
        <h4 className="font-semibold">Caller Information</h4>
        <div className="mt-2">Phone: {call.phone}</div>
        <div>Location: {call.location}</div>
        <div>Time: {call.time}</div>
        <div className="mt-2 muted">Transcript:</div>
        <div className="mt-1 text-sm">{call.transcript || '—'}</div>
        <div className="mt-2 muted">AI Summary:</div>
        <div className="mt-1 text-sm">{call.ai_summary || '—'}</div>
      </div>

      <div className="card p-4 rounded">
        <h4 className="font-semibold">Incident Information</h4>
        <div className="mt-2">Type: {call.incident_type || 'N/A'}</div>
        <div>Priority: {call.priority || 'N/A'}</div>
        <div className="mt-2">Recommended Agencies: {call.recommended_agencies?.join(', ') || 'N/A'}</div>
        <div className="mt-4 flex flex-col gap-2">
          <button className="py-2 card rounded">Assign Police</button>
          <button className="py-2 card rounded">Assign Ambulance</button>
          <button className="py-2 card rounded">Escalate Incident</button>
        </div>
      </div>
    </div>
  )
}
