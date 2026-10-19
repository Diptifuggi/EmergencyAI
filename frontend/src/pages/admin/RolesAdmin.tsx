// @ts-nocheck
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { listRoles } from '@/api/usersApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import Card from '@/components/common/Card'

export default function RolesAdmin(){
  const { data: roles = [], isLoading, error } = useQuery({
    queryKey: ['roles'],
    queryFn: () => listRoles(),
    refetchInterval: 30000,
  })
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
                <td className="py-3 text-sm text-zinc-600">{role.permissions ?? 'Not available'}</td>
                <td className="py-3 text-sm text-zinc-600">{role.description ?? 'Not available'}</td>
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
