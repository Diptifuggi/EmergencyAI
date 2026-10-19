// @ts-nocheck
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { listUsers } from '@/api/usersApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import Card from '@/components/common/Card'

export default function UsersAdmin(){
  const { data: responseUsers = [], isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => listUsers(),
    refetchInterval: 30000,
  })
  const users = responseUsers.map(user => ({
    id: user.id,
    full_name: user.username || 'Not available',
    email: user.email || 'Not available',
    role: user.role_name || 'Not available',
    status: user.is_active ? 'Active' : 'Inactive',
    phone: 'Not available',
    department: 'Not available',
    last_login: 'Not available',
  }))
  if (isLoading) return <Loading />
  if (error) return <ErrorMessage error={error} />
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Users</h1>
      <Card>
        <table className="w-full text-left">
          <thead>
            <tr>
              <th className="pb-3">ID</th>
              <th className="pb-3">Name</th>
              <th className="pb-3">Email</th>
              <th className="pb-3">Role</th>
              <th className="pb-3">Department</th>
              <th className="pb-3">Phone</th>
              <th className="pb-3">Status</th>
              <th className="pb-3">Last Login</th>
              <th className="pb-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id} className="border-t">
                <td className="py-3 text-xs font-mono text-zinc-600">{user.id}</td>
                <td className="py-3 font-medium text-sm text-zinc-900">{user.full_name}</td>
                <td className="py-3 text-sm text-zinc-600">{user.email}</td>
                <td className="py-3 text-sm text-zinc-700">{user.role}</td>
                <td className="py-3 text-sm text-zinc-600">{user.department}</td>
                <td className="py-3 text-sm text-zinc-600">{user.phone}</td>
                <td className="py-3">
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${user.status === 'Active' ? 'bg-emerald-100 text-emerald-800' : user.status === 'Busy' ? 'bg-amber-100 text-amber-800' : 'bg-zinc-100 text-zinc-500'}`}>
                    {user.status}
                  </span>
                </td>
                <td className="py-3 text-sm text-zinc-600">{user.last_login}</td>
                <td className="py-3 space-x-2">
                  <button className="text-xs text-blue-600 hover:underline">View</button>
                  <button className="text-xs text-zinc-900 hover:underline">Edit</button>
                  <button className="text-xs text-red-600 hover:underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
