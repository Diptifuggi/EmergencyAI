// @ts-nocheck
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { listUsers } from '@/api/usersApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import Card from '@/components/common/Card'

export default function UsersAdmin(){
  // const { data, isLoading, error } = useQuery({ queryKey: ['users'], queryFn: () => listUsers() })
  // TODO: Replace with backend API
  const users = [
    {
      id: 'USR-001',
      full_name: 'Admin User',
      email: 'admin@emergencyiq.in',
      role: 'Administrator',
      status: 'Active',
      phone: '+91 9876543210',
      department: 'System Administration',
      last_login: '5 min ago',
    },
    {
      id: 'USR-002',
      full_name: 'Rahul Sharma',
      email: 'rahul@emergencyiq.in',
      role: 'Dispatcher',
      status: 'Active',
      phone: '+91 9876500001',
      department: 'Police Control Room',
      last_login: '12 min ago',
    },
    {
      id: 'USR-003',
      full_name: 'Priya Patel',
      email: 'priya@emergencyiq.in',
      role: 'Medical Operator',
      status: 'Active',
      phone: '+91 9876500002',
      department: 'Health Department',
      last_login: '30 min ago',
    },
    {
      id: 'USR-004',
      full_name: 'Amit Verma',
      email: 'amit@emergencyiq.in',
      role: 'Fire Dispatcher',
      status: 'Offline',
      phone: '+91 9876500003',
      department: 'Fire Brigade',
      last_login: '1 hour ago',
    },
    {
      id: 'USR-005',
      full_name: 'Sneha Joshi',
      email: 'sneha@emergencyiq.in',
      role: 'Women Safety',
      status: 'Active',
      phone: '+91 9876500004',
      department: 'Women Helpline',
      last_login: '2 hours ago',
    },
    {
      id: 'USR-006',
      full_name: 'Rohan Mehta',
      email: 'rohan@emergencyiq.in',
      role: 'Cyber Cell',
      status: 'Busy',
      phone: '+91 9876500005',
      department: 'Cyber Crime',
      last_login: 'Just now',
    },
  ]
  const isLoading = false
  const error = null
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
