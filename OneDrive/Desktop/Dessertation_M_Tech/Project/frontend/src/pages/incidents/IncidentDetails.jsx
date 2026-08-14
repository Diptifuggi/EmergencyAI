import React from 'react'
import { useParams } from 'react-router-dom'
import useApi from '../../hooks/useApi'
import incidentService from '../../services/incidentService'

export default function IncidentDetails() {
  const { id } = useParams()
  const incident = useApi(() => incidentService.get(id), [id])

  if (incident.loading) return <div>Loading…</div>
  if (!incident.data) return <div>Not found</div>

  return <div className="p-4 bg-white rounded shadow">Incident details for {id}</div>
}
