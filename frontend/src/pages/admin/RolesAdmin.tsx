// @ts-nocheck
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { listRoles } from '@/api/usersApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import Card from '@/components/common/Card'

export default function RolesAdmin(){
  // const { data, isLoading, error } = useQuery({ queryKey: ['roles'], queryFn: () => listRoles() })
  // TODO: Replace with backend API
  const roles = [
    { id: 1, name: 'Administrator', users: 2, permissions: 42, description: 'Full platform access' },
    { id: 2, name: 'Dispatcher', users: 12, permissions: 18, description: 'Handle emergency calls' },
    { id: 3, name: 'Medical Operator', users: 7, permissions: 14, description: 'Medical incidents' },
    { id: 4, name: 'Police Officer', users: 16, permissions: 20, description: 'Law enforcement' },
    { id: 5, name: 'Fire Officer', users: 9, permissions: 15, description: 'Fire emergencies' },
    { id: 6, name: 'Viewer', users: 5, permissions: 4, description: 'Read only access' },
  ]
  const isLoading = false
  const error = null
  if (isLoading) return <Loading />
  if (error) return <ErrorMessage error={error} />
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Roles</h1>
      <Card>
        <table className="w-full text-left">
          <thead>
            <tr>
              <th className="pb-3">Role</th>
              <th className="pb-3">Users</th>
              <th className="pb-3">Permissions</th>
              <th className="pb-3">Description</th>
              <th className="pb-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {roles.map(role => (
              <tr key={role.id} className="border-t">
                <td className="py-3 text-sm text-zinc-900 font-medium">{role.name}</td>
                <td className="py-3 text-sm text-zinc-600">{role.users}</td>
                <td className="py-3 text-sm text-zinc-600">{role.permissions}</td>
                <td className="py-3 text-sm text-zinc-600">{role.description}</td>
                <td className="py-3 space-x-2">
                  <button className="text-xs text-blue-600 hover:underline">View</button>
                  <button className="text-xs text-zinc-900 hover:underline">Edit</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
