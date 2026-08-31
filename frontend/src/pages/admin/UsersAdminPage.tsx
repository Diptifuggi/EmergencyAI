// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axiosClient from '@/api/axiosClient'
import { formatDate } from '@/lib/formatters'
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Select, Table, TableHeader, TableBody, TableRow, TableCell, TableHead, TableCaption, Badge } from '@/components/ui'
import AddUserDialog from '@/components/admin/AddUserDialog'
import EditUserDialog from '@/components/admin/EditUserDialog'
import ConfirmDialog from '@/components/ConfirmDialog'
import { Pencil, Power } from 'lucide-react'
import { toastSuccess, toastError } from '@/lib/toast'

const ROLE_BADGES = {
  Admin: 'bg-zinc-900 text-white',
  Dispatcher: 'bg-zinc-700 text-white',
  Police: 'bg-zinc-500 text-white',
  Fire: 'bg-zinc-500 text-white',
  Ambulance: 'bg-zinc-500 text-white',
  Analyst: 'bg-zinc-300 text-zinc-800',
}

export default function UsersAdminPage(){
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [q, setQ] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [editUser, setEditUser] = useState(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['admin','users', page, pageSize, q, roleFilter],
    queryFn: async () => {
      const params = { page, page_size: pageSize }
      if (q) params.q = q
      if (roleFilter) params.role = roleFilter
      const resp = await axiosClient.get('/users', { params })
      return resp.data
    },
    keepPreviousData: true,
  })

  const users = data?.items || data || []
  const total = data?.total || (Array.isArray(data) ? data.length : users.length)

  const stats = useMemo(() => ({
    total: total || 0,
    active: users.filter(u=>u.is_active).length,
    inactive: users.filter(u=>!u.is_active).length,
  }), [users, total])

  const toggleActive = useMutation({
    mutationFn: async ({ id, active }) => {
      const resp = await axiosClient.patch(`/users/${id}`, { is_active: active })
      return resp.data
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin','users'] }); toastSuccess('User updated') },
    onError: (e) => { toastError(e?.response?.data?.detail || e?.message || 'Failed to update user') }
  })

  function handleToggle(u){
    setConfirmTarget(u)
    setConfirmOpen(true)
  }

  const [confirmOpen, setConfirmOpen] = React.useState(false)
  const [confirmTarget, setConfirmTarget] = React.useState(null)

  function doConfirmToggle(){
    if (!confirmTarget) return
    toggleActive.mutate({ id: confirmTarget.id, active: !confirmTarget.is_active })
    setConfirmOpen(false)
    setConfirmTarget(null)
  }

  useEffect(()=>{ refetch() }, [page, pageSize, q, roleFilter])

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">User Management</h1>
          <div className="text-sm text-gray-600">Manage operator accounts</div>
        </div>
        <div className="flex items-center gap-3">
          <div className="grid grid-cols-3 gap-3 mr-4">
            <div className="bg-white p-3 rounded shadow text-center"><div className="text-sm text-gray-500">Total Users</div><div className="text-lg font-bold">{stats.total}</div></div>
            <div className="bg-white p-3 rounded shadow text-center"><div className="text-sm text-gray-500">Active</div><div className="text-lg font-bold text-green-600">{stats.active}</div></div>
            <div className="bg-white p-3 rounded shadow text-center"><div className="text-sm text-gray-500">Inactive</div><div className="text-lg font-bold text-red-600">{stats.inactive}</div></div>
          </div>
          <Button onClick={()=> setAddOpen(true)} className="bg-black text-white">Add User</Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              <Select value={roleFilter} onChange={(e)=> setRoleFilter(e.target.value)}>
                <option value="">All Roles</option>
                {Object.keys(ROLE_BADGES).map(r => <option key={r} value={r}>{r}</option>)}
              </Select>
              <Input placeholder="Search name or email" value={q} onChange={(e)=> setQ(e.target.value)} />
              <Button onClick={() => { const csv = JSON.stringify(users); const blob = new Blob([csv], { type: 'text/csv' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `users-${new Date().toISOString()}.csv`; a.click(); URL.revokeObjectURL(url); }}>Export</Button>
            </div>
            <div className="text-sm text-gray-500">Showing {users.length} of {total}</div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                new Array(10).fill(0).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><div className="h-4 bg-gray-100 animate-pulse w-24" /></TableCell>
                    <TableCell><div className="h-4 bg-gray-100 animate-pulse w-32" /></TableCell>
                    <TableCell><div className="h-4 bg-gray-100 animate-pulse w-20" /></TableCell>
                    <TableCell><div className="h-4 bg-gray-100 animate-pulse w-16" /></TableCell>
                    <TableCell><div className="h-4 bg-gray-100 animate-pulse w-16" /></TableCell>
                    <TableCell><div className="h-4 bg-gray-100 animate-pulse w-20" /></TableCell>
                    <TableCell><div className="h-4 bg-gray-100 animate-pulse w-20" /></TableCell>
                  </TableRow>
                ))
              ) : (
                users.map((u: any) => (
                  <TableRow key={u.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-800">{(u.full_name || u.username || '').slice(0, 2).toUpperCase()}</div>
                        <div>
                          <div className="font-medium">{u.full_name || u.username}</div>
                          <div className="text-xs text-gray-500">{u.username}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{u.email}</TableCell>
                    <TableCell>{u.phone || '—'}</TableCell>
                    <TableCell><span className={`px-2 py-1 rounded text-xs ${ROLE_BADGES[u.role_name] || 'bg-zinc-200 text-zinc-800'}`}>{u.role_name || 'Operator'}</span></TableCell>
                    <TableCell>{u.is_active ? <Badge className="bg-green-100 text-green-800">Active</Badge> : <Badge className="bg-red-100 text-red-800">Inactive</Badge>}</TableCell>
                    <TableCell>{formatDate(u.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <button onClick={() => setEditUser(u)} className="p-1 rounded hover:bg-gray-50"><Pencil className="w-4 h-4" /></button>
                        <button onClick={() => handleToggle(u)} className="p-1 rounded hover:bg-gray-50"><Power className="w-4 h-4" /></button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>

          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-gray-600">Showing {users.length} users</div>
            <div className="flex items-center gap-2">
              <Button disabled={page<=1} onClick={()=> setPage(p=>Math.max(1,p-1))}>Prev</Button>
              <div>Page {page}</div>
              <Button disabled={users.length < pageSize} onClick={()=> setPage(p=>p+1)}>Next</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {addOpen && <AddUserDialog open={addOpen} onClose={() => { setAddOpen(false); qc.invalidateQueries({ queryKey: ['admin','users'] }) }} />}
      {editUser && <EditUserDialog user={editUser} onClose={() => { setEditUser(null); qc.invalidateQueries({ queryKey: ['admin','users'] }) }} />}
      <ConfirmDialog open={confirmOpen} title="Confirm User Status Change" message={confirmTarget ? `Are you sure you want to ${confirmTarget.is_active ? 'deactivate' : 'activate'} ${confirmTarget.full_name || confirmTarget.username}?` : ''} onConfirm={doConfirmToggle} onCancel={()=>setConfirmOpen(false)} confirmText="Confirm" />
    </div>
  )
}
