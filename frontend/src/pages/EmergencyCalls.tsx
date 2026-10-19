// @ts-nocheck
import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getEmergencies } from '@/api/emergencyApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import Card from '@/components/common/Card'
import { useNavigate } from 'react-router-dom'
import { toEmergencyCallRow } from '@/types/emergency'

export default function EmergencyCalls() {
  const navigate = useNavigate()
  const [searchText, setSearchText] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('All Priorities')
  const { data: apiCalls = [], isLoading, error } = useQuery({
    queryKey: ['emergency-calls'],
    queryFn: () => getEmergencies({ limit: 200, offset: 0 }),
    refetchInterval: 10000,
    staleTime: 5000,
  })
  const calls = apiCalls.map(toEmergencyCallRow)

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
