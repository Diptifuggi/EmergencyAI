import React from 'react'
import { useParams } from 'react-router-dom'
import useApi from '../../hooks/useApi'
import callService from '../../services/callService'
import CallDetailsWorkspace from '../../components/CallDetailsWorkspace'

export default function CallDetails() {
  const { id } = useParams()
  const call = useApi(() => callService.get(id), [id])

  if (call.loading) return <div className="p-4 muted">Loading…</div>
  if (!call.data) return <div className="p-4 muted">Not found</div>

  return (
    <div className="p-4">
      <CallDetailsWorkspace call={call.data} />
    </div>
  )
}
