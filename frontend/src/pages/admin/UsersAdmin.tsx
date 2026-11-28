// @ts-nocheck
import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listUsers, createUser, updateUser, resetUserPassword } from '@/api/usersApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import Card from '@/components/common/Card'
import toast from 'react-hot-toast'

export default function UsersAdmin() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [resetTarget, setResetTarget] = useState<any>(null)
  const [newPassword, setNewPassword] = useState('')
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    role_name: 'Operator',
  })

  const { data: responseUsers = [], isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => listUsers(),
    refetchInterval: 30000,
  })

  const createMutation = useMutation({
    mutationFn: (payload: any) => createUser(payload),
    onSuccess: () => {
      toast.success('Account created')
      setShowCreate(false)
      setForm({ username: '', email: '', password: '', role_name: 'Operator' })
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to create user')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateUser(id, data),
    onSuccess: () => {
      toast.success('User updated')
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to update user')
    },
  })

  const resetMutation = useMutation({
    mutationFn: ({ id, password }: { id: string; password: string }) =>
      resetUserPassword(id, password),
    onSuccess: () => {
      toast.success('Password reset & active sessions revoked')
      setResetTarget(null)
      setNewPassword('')
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to reset password')
    },
  })

  if (isLoading) return <Loading />
  if (error) return <ErrorMessage error={error} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">User & Operator Management</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-black text-white text-sm font-medium rounded-lg hover:bg-zinc-800"
        >
          + Create Operator / Admin
        </button>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-xs uppercase text-zinc-500 border-b">
                <th className="pb-3">Username</th>
                <th className="pb-3">Email</th>
                <th className="pb-3">Role</th>
                <th className="pb-3">Status</th>
                <th className="pb-3">Created</th>
                <th className="pb-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {responseUsers.map((user: any) => (
                <tr key={user.id} className="border-t text-sm">
                  <td className="py-3 font-medium text-zinc-900">{user.username}</td>
                  <td className="py-3 text-zinc-600">{user.email}</td>
                  <td className="py-3">
                    <select
                      value={user.role_name}
                      onChange={(e) =>
                        updateMutation.mutate({
                          id: user.id,
                          data: { role_name: e.target.value },
                        })
                      }
                      className="border rounded px-2 py-1 text-xs bg-white"
                    >
                      <option value="User">User</option>
                      <option value="Operator">Operator</option>
                      <option value="Supervisor">Supervisor</option>
                      <option value="Admin">Admin</option>
                    </select>
                  </td>
                  <td className="py-3">
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                        user.is_active
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {user.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="py-3 text-xs text-zinc-500">
                    {user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="py-3 text-right space-x-3">
                    <button
                      onClick={() =>
                        updateMutation.mutate({
                          id: user.id,
                          data: { is_active: !user.is_active },
                        })
                      }
                      className={`text-xs font-medium hover:underline ${
                        user.is_active ? 'text-red-600' : 'text-emerald-600'
                      }`}
                    >
                      {user.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => setResetTarget(user)}
                      className="text-xs text-blue-600 font-medium hover:underline"
                    >
                      Reset Password
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {showCreate && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 max-w-md w-full space-y-4 shadow-xl">
            <h2 className="text-lg font-bold">Create Operator / Staff Account</h2>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Username"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
              <input
                type="email"
                placeholder="Email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
              <input
                type="password"
                placeholder="Password (min 8, upper, lower, digit)"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
              <select
                value={form.role_name}
                onChange={(e) => setForm({ ...form, role_name: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              >
                <option value="Operator">Operator</option>
                <option value="Supervisor">Supervisor</option>
                <option value="Admin">Admin</option>
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowCreate(false)}
                className="px-3 py-1.5 text-sm text-zinc-600"
              >
                Cancel
              </button>
              <button
                disabled={createMutation.isPending}
                onClick={() => createMutation.mutate(form)}
                className="px-4 py-1.5 text-sm bg-black text-white rounded-lg"
              >
                {createMutation.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {resetTarget && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 max-w-md w-full space-y-4 shadow-xl">
            <h2 className="text-lg font-bold">Reset Password for {resetTarget.username}</h2>
            <input
              type="password"
              placeholder="New Password (min 8, upper, lower, digit)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setResetTarget(null)
                  setNewPassword('')
                }}
                className="px-3 py-1.5 text-sm text-zinc-600"
              >
                Cancel
              </button>
              <button
                disabled={resetMutation.isPending}
                onClick={() =>
                  resetMutation.mutate({ id: resetTarget.id, password: newPassword })
                }
                className="px-4 py-1.5 text-sm bg-red-600 text-white rounded-lg"
              >
                {resetMutation.isPending ? 'Resetting...' : 'Reset & Revoke Sessions'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
