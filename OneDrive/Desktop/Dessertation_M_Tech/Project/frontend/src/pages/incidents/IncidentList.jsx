import React from 'react'
import PageHeader from '../../components/common/PageHeader'
import useApi from '../../hooks/useApi'
import incidentService from '../../services/incidentService'
import EmptyState from '../../components/common/EmptyState'

export default function IncidentList() {
  const incidents = useApi(() => incidentService.list())

  if (incidents.loading) return <div>Loading…</div>
  if (!incidents.data || incidents.data.length === 0) return <EmptyState title="No incidents" />

  return (
    <div>
      <PageHeader title="Incidents" />
      <div className="bg-white rounded shadow p-4">Incident list rendering from API</div>
    </div>
  )
}
