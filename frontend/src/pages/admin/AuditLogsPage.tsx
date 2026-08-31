// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import axiosClient from '@/api/axiosClient'
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Select, Badge } from '@/components/ui'
import { formatDate } from '@/lib/formatters'
import { Copy } from 'lucide-react'

function downloadCSV(rows, filename) {
  if (!rows || rows.length === 0) return
  const keys = Object.keys(rows[0])
  const csv = [keys.join(',')].concat(rows.map(r => keys.map(k => `"${String(r[k] ?? '')}"`).join(','))).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url)
}

export default function AuditLogsPage(){
  const [page, setPage] = useState(1)
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [userFilter, setUserFilter] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const [entityFilter, setEntityFilter] = useState('')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['audit', page, from, to, userFilter, actionFilter, entityFilter],
    queryFn: async () => {
      const params = { page, page_size: 50 }
      if (from) params.from = from
      if (to) params.to = to
      if (userFilter) params.user = userFilter
      if (actionFilter) params.action = actionFilter
      if (entityFilter) params.entity = entityFilter
      const r = await axiosClient.get('/audit-logs', { params })
      return r.data
    }
  })

  const rows = data?.items || data || []
  const total = data?.total || rows.length

  useEffect(()=>{ refetch() }, [page])

  const [copied, setCopied] = useState(null)
  const handleCopy = async (text, id) => {
    try { await navigator.clipboard.writeText(text); setCopied(id); setTimeout(()=>setCopied(null),2000) } catch(e){}
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">Audit Logs</h1>
          <div className="text-sm text-gray-600">Full audit trail for compliance and security review</div>
        </div>
        <div>
          <Button onClick={()=> downloadCSV(rows, `emergencyiq-audit-${new Date().toISOString().slice(0,10)}.csv`)}>Export CSV</Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Input type="date" value={from} onChange={(e)=>setFrom(e.target.value)} />
            <Input type="date" value={to} onChange={(e)=>setTo(e.target.value)} />
            <Input placeholder="User" value={userFilter} onChange={(e)=>setUserFilter(e.target.value)} />
            <Input placeholder="Action" value={actionFilter} onChange={(e)=>setActionFilter(e.target.value)} />
            <Input placeholder="Entity" value={entityFilter} onChange={(e)=>setEntityFilter(e.target.value)} />
            <Button onClick={()=>{ setPage(1); refetch() }}>Apply</Button>
            <Button variant="secondary" onClick={()=>{ setFrom(''); setTo(''); setUserFilter(''); setActionFilter(''); setEntityFilter(''); refetch() }}>Clear</Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-auto">
            {isLoading ? (
              <div>
                {new Array(8).fill(0).map((_,i)=>(<div key={i} className="h-10 bg-gray-100 animate-pulse mb-2 rounded"/>))}
              </div>
            ) : rows.length === 0 ? (
              <div className="p-8 text-center text-gray-600">No audit logs found</div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left"><th>Time</th><th>User</th><th>Action</th><th>Entity Type</th><th>Entity ID</th><th/></tr>
                </thead>
                <tbody>
                  {rows.map(r => (
                    <tr key={r.id} className="border-t">
                      <td className="py-2 align-top">{formatDate(r.time)}</td>
                      <td className="py-2 align-top">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-800">{(r.user?.full_name||'S').slice(0,1)}</div>
                          <div>{r.user?.full_name || 'System'}</div>
                        </div>
                      </td>
                      <td className="py-2 align-top">
                        <div className={`${r.action?.includes('created') ? 'text-green-700' : r.action?.includes('updated') ? 'text-blue-700' : r.action?.includes('deleted') ? 'text-red-700' : r.action?.includes('dispatched') ? 'text-orange-700' : 'text-zinc-600'}`}>{r.action}</div>
                      </td>
                      <td className="py-2 align-top"><Badge className="bg-gray-100 text-gray-700">{r.entity_type}</Badge></td>
                      <td className="py-2 align-top">{(r.entity_id || '').slice(0,8)} <button onClick={()=>handleCopy(r.entity_id, r.id)} className="ml-2 text-gray-500"><Copy className="w-4 h-4 inline" /></button> {copied === r.id && <span className="text-green-600">✓</span>}</td>
                      <td/>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-gray-600">Showing {rows.length} of {total}</div>
            <div className="flex items-center gap-2">
              <Button disabled={page<=1} onClick={()=> setPage(p=>Math.max(1,p-1))}>Prev</Button>
              <div>Page {page}</div>
              <Button disabled={rows.length < 50} onClick={()=> setPage(p=>p+1)}>Next</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
