import React from 'react'
import PageHeader from '../../components/common/PageHeader'
import useApi from '../../hooks/useApi'
import callService from '../../services/callService'
import EmptyState from '../../components/common/EmptyState'

export default function CallsList() {
  const calls = useApi(() => callService.list())

  if (calls.loading) return <div>Loading…</div>
  if (!calls.data || calls.data.length === 0) return <EmptyState title="No calls" />

  return (
    <div>
      <PageHeader title="Emergency Calls" />
      <div className="bg-white rounded shadow p-4">List rendering based on API</div>
    </div>
  )
}
