// @ts-nocheck
import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getEmergencies } from '@/api/emergencyApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import Card from '@/components/common/Card'
import { Link, useNavigate } from 'react-router-dom'

export default function EmergencyCalls() {
  const navigate = useNavigate()
  const [searchText, setSearchText] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('All Priorities')

  // const [filters, setFilters] = useState({})
  // const { data, isLoading, error } = useQuery({ queryKey: ['emergencies', filters], queryFn: () => getEmergencies(filters) })
  // ── MOCK DATA (temporary) ─────────────────────────────────
  // TODO: Remove these 2 lines and uncomment useQuery above
  //       when backend API is ready at GET /api/v1/calls
  const calls = [
    {
      id: 'CALL-001',
      caller_name: 'Ramesh Patel',
      caller_phone: '+91 98765 43210',
      category: 'Road Accident',
      priority_level: 'Critical',
      priority_bg: 'bg-red-100',
      priority_text: 'text-red-800',
      dot: 'bg-red-600',
      border: 'border-l-red-600',
      location: 'Silvassa Main Road',
      time_ago: '2m ago',
      status: 'Processing',
      status_bg: 'bg-yellow-100',
      status_text: 'text-yellow-800',
    },
    {
      id: 'CALL-002',
      caller_name: 'Priya Sharma',
      caller_phone: '+91 87654 32109',
      category: 'Medical Emergency',
      priority_level: 'Very High',
      priority_bg: 'bg-orange-100',
      priority_text: 'text-orange-800',
      dot: 'bg-orange-500',
      border: 'border-l-orange-500',
      location: 'Vapi Hospital Road',
      time_ago: '8m ago',
      status: 'Assigned',
      status_bg: 'bg-blue-100',
      status_text: 'text-blue-800',
    },
    {
      id: 'CALL-003',
      caller_name: 'Ankit Mehta',
      caller_phone: '+91 76543 21098',
      category: 'Fire',
      priority_level: 'High',
      priority_bg: 'bg-amber-100',
      priority_text: 'text-amber-800',
      dot: 'bg-amber-500',
      border: 'border-l-amber-500',
      location: 'GIDC Industrial Area',
      time_ago: '15m ago',
      status: 'Pending',
      status_bg: 'bg-zinc-100',
      status_text: 'text-zinc-700',
    },
    {
      id: 'CALL-004',
      caller_name: 'Sunita Kadam',
      caller_phone: '+91 65432 10987',
      category: 'Women Safety',
      priority_level: 'High',
      priority_bg: 'bg-amber-100',
      priority_text: 'text-amber-800',
      dot: 'bg-amber-500',
      border: 'border-l-amber-500',
      location: 'Near Railway Station',
      time_ago: '22m ago',
      status: 'Processing',
      status_bg: 'bg-yellow-100',
      status_text: 'text-yellow-800',
    },
    {
      id: 'CALL-005',
      caller_name: 'Vijay Rathod',
      caller_phone: '+91 54321 09876',
      category: 'Natural Disaster',
      priority_level: 'Moderate',
      priority_bg: 'bg-green-100',
      priority_text: 'text-green-800',
      dot: 'bg-green-600',
      border: 'border-l-transparent',
      location: 'NH48 Highway',
      time_ago: '31m ago',
      status: 'Resolved',
      status_bg: 'bg-green-100',
      status_text: 'text-green-800',
    },
    {
      id: 'CALL-006',
      caller_name: 'Meena Joshi',
      caller_phone: '+91 43210 98765',
      category: 'Medical Emergency',
      priority_level: 'Critical',
      priority_bg: 'bg-red-100',
      priority_text: 'text-red-800',
      dot: 'bg-red-600',
      border: 'border-l-red-600',
      location: 'Silvassa Civil Hospital',
      time_ago: '45m ago',
      status: 'Assigned',
      status_bg: 'bg-blue-100',
      status_text: 'text-blue-800',
    },
    {
      id: 'CALL-007',
      caller_name: 'Rohit Desai',
      caller_phone: '+91 32109 87654',
      category: 'Cyber Crime',
      priority_level: 'Low',
      priority_bg: 'bg-blue-100',
      priority_text: 'text-blue-800',
      dot: 'bg-blue-500',
      border: 'border-l-transparent',
      location: 'Vapi City Center',
      time_ago: '1h ago',
      status: 'Pending',
      status_bg: 'bg-zinc-100',
      status_text: 'text-zinc-700',
    },
    {
      id: 'CALL-008',
      caller_name: 'Kavita Nair',
      caller_phone: '+91 21098 76543',
      category: 'Child Abuse',
      priority_level: 'Very High',
      priority_bg: 'bg-orange-100',
      priority_text: 'text-orange-800',
      dot: 'bg-orange-500',
      border: 'border-l-orange-500',
      location: 'Dadra North Sector',
      time_ago: '1h 20m ago',
      status: 'Processing',
      status_bg: 'bg-yellow-100',
      status_text: 'text-yellow-800',
    },
  ]
  const isLoading = false
  const error = null
  // ──────────────────────────────────────────────────────────

  const filteredCalls = calls.filter(call => {
    const matchSearch = searchText === '' ||
      call.caller_name.toLowerCase().includes(searchText.toLowerCase()) ||
      call.caller_phone.includes(searchText) ||
      call.category.toLowerCase().includes(searchText.toLowerCase()) ||
      call.id.toLowerCase().includes(searchText.toLowerCase())
    const matchPriority = priorityFilter === 'All Priorities' ||
      call.priority_level === priorityFilter
    return matchSearch && matchPriority
  })

  if (isLoading) return <Loading />
  if (error) return <ErrorMessage error={error} />

  return (
    <div>
      <Card title={<span>Emergency Calls<span className="ml-2 bg-zinc-900 text-white text-xs font-medium px-2 py-0.5 rounded-full">{filteredCalls.length}</span></span>}>
        <div className="mb-4 flex gap-2">
          <input
            aria-label="search"
            placeholder="Search"
            className="border p-2 rounded"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="border p-2 rounded"
          >
            <option>All Priorities</option>
            <option>Critical</option>
            <option>Very High</option>
            <option>High</option>
            <option>Moderate</option>
            <option>Low</option>
          </select>
        </div>

        <table className="w-full text-left">
          <thead>
            <tr>
              <th>Call ID</th>
              <th>Caller</th>
              <th>Category</th>
              <th>Priority</th>
              <th>Location</th>
              <th>Time</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredCalls.map(call => (
              <tr key={call.id} className={`border-l-4 ${call.border}`}>
                <td>
                  <span className="font-mono text-xs font-semibold bg-zinc-100 text-zinc-700 px-2 py-0.5 rounded">
                    {call.id}
                  </span>
                </td>
                <td>
                  <div className="font-medium text-sm text-zinc-900">{call.caller_name}</div>
                  <div className="text-xs text-zinc-500 mt-0.5">{call.caller_phone}</div>
                </td>
                <td className="text-sm text-zinc-700">{call.category}</td>
                <td>
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${call.priority_bg} ${call.priority_text}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${call.dot}`} />
                    {call.priority_level}
                  </span>
                </td>
                <td className="text-sm text-zinc-600">{call.location}</td>
                <td className="text-sm text-zinc-500">{call.time_ago}</td>
                <td>
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${call.status_bg} ${call.status_text}`}>
                    {call.status}
                  </span>
                </td>
                <td>
                  <button
                    onClick={() => navigate(`/calls/${call.id}`)}
                    className="text-xs font-medium text-zinc-900 border border-zinc-300 px-3 py-1.5 rounded-md hover:bg-zinc-50 transition-colors"
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
