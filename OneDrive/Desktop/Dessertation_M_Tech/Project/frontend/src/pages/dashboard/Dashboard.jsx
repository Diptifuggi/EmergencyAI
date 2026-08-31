import React from 'react'
import PageHeader from '../../components/common/PageHeader'
import useApi from '../../hooks/useApi'
import callService from '../../services/callService'
import incidentService from '../../services/incidentService'
import healthService from '../../services/healthService'
import MetricCards from '../../components/MetricCards'
import EmergencyQueueTable from '../../components/EmergencyQueueTable'
import IncidentCorrelationPanel from '../../components/IncidentCorrelationPanel'
import SeverityChart from '../../components/SeverityChart'
import DispatchPanel from '../../components/DispatchPanel'

export default function Dashboard() {
  const calls = useApi(() => callService.list())
  const incidents = useApi(() => incidentService.list())
  const health = useApi(() => healthService.health())
  const healthDb = useApi(() => healthService.healthDb())

  const metrics = [
    { key: 'active', title: 'Active Calls', value: calls.data?.active || 0 },
    { key: 'critical', title: 'Critical Calls', value: calls.data?.critical || 0 },
    { key: 'open', title: 'Open Incidents', value: incidents.data?.open || 0 },
    { key: 'resources', title: 'Resources Dispatched', value: 0 },
    { key: 'avg', title: 'Avg Response Time', value: incidents.data?.avg_response_time || '-' }
  ]

  const severityData = incidents.data?.severity_distribution || []
  const queueData = calls.data?.items || []
  const clusters = incidents.data?.clusters || []
  const agencies = [{ name: 'Police', status: 'Active', count: 12 }, { name: 'Fire', status: 'Active', count: 6 }, { name: 'Ambulance', status: 'Active', count: 4 }]

  return (
    <div>
      <PageHeader title="Command Center" subtitle="Emergency Operations Overview" />

      <div className="mt-2 flex gap-4">
        <div className="card p-3 rounded flex items-center gap-3">
          <div className="text-sm muted">Backend</div>
          <div className="font-semibold">{health.loading ? 'Checking...' : health.data?.status === 'ok' ? 'Connected' : 'Disconnected'}</div>
        </div>

        <div className="card p-3 rounded flex items-center gap-3">
          <div className="text-sm muted">Database</div>
          <div className="font-semibold">{healthDb.loading ? 'Checking...' : healthDb.data?.status === 'ok' ? 'Connected' : 'Disconnected'}</div>
        </div>
      </div>

      <div className="mt-4">
        <MetricCards metrics={metrics} />
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <EmergencyQueueTable data={queueData} />
        </div>

        <div className="space-y-4">
          <IncidentCorrelationPanel clusters={clusters} />
          <SeverityChart data={severityData} />
          <DispatchPanel agencies={agencies} />
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-4 rounded">Emergency Trends (placeholder)</div>
        <div className="card p-4 rounded">Emergency Categories (placeholder)</div>
        <div className="card p-4 rounded">Recent Incident Activity</div>
      </div>
    </div>
  )
}
