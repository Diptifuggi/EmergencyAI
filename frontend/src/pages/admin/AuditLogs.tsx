// @ts-nocheck
import React from 'react'
import Card from '@/components/common/Card'

export default function AuditLogs(){
  const auditLogs: any[] = []
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
            {auditLogs.length === 0 && (
              <tr className="border-t">
                <td className="py-3 text-sm text-zinc-500" colSpan={6}>No audit log data available from the backend.</td>
              </tr>
            )}
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
