// @ts-nocheck
import React from 'react'
import Card from '@/components/common/Card'

export default function AuditLogs(){
  // TODO: Replace with backend API
  const auditLogs = [
    { id: 'AUD-001', user: 'Admin User', action: 'Created User', module: 'User Management', time: '2 min ago', status: 'Success' },
    { id: 'AUD-002', user: 'Rahul Sharma', action: 'Assigned Emergency Call', module: 'Dispatch', time: '8 min ago', status: 'Success' },
    { id: 'AUD-003', user: 'Priya Patel', action: 'Updated Incident', module: 'Incidents', time: '15 min ago', status: 'Success' },
    { id: 'AUD-004', user: 'System', action: 'Automatic Severity Analysis', module: 'AI Engine', time: '21 min ago', status: 'Completed' },
    { id: 'AUD-005', user: 'Admin User', action: 'Deleted User', module: 'User Management', time: '40 min ago', status: 'Warning' },
    { id: 'AUD-006', user: 'Rohan Mehta', action: 'Failed Login', module: 'Authentication', time: '1 hour ago', status: 'Failed' },
    { id: 'AUD-007', user: 'System', action: 'Database Backup', module: 'Maintenance', time: '2 hours ago', status: 'Completed' },
    { id: 'AUD-008', user: 'Sneha Joshi', action: 'Closed Incident', module: 'Incidents', time: '3 hours ago', status: 'Success' },
  ]
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Audit Logs</h1>
      <Card>
        <table className="w-full text-left">
          <thead>
            <tr>
              <th className="pb-3">Log ID</th>
              <th className="pb-3">User</th>
              <th className="pb-3">Module</th>
              <th className="pb-3">Action</th>
              <th className="pb-3">Time</th>
              <th className="pb-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {auditLogs.map(log => (
              <tr key={log.id} className="border-t">
                <td className="py-3 text-xs font-mono text-zinc-600">{log.id}</td>
                <td className="py-3 text-sm text-zinc-900">{log.user}</td>
                <td className="py-3 text-sm text-zinc-600">{log.module}</td>
                <td className="py-3 text-sm text-zinc-600">{log.action}</td>
                <td className="py-3 text-sm text-zinc-600">{log.time}</td>
                <td className="py-3">
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${log.status === 'Success' ? 'bg-emerald-100 text-emerald-800' : log.status === 'Completed' ? 'bg-blue-100 text-blue-800' : log.status === 'Warning' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'}`}>
                    {log.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
