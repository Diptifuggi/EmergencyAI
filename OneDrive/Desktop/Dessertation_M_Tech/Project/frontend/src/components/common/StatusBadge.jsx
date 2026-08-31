import React from 'react'

const map = {
  critical: 'bg-red-100 text-red-800',
  warning: 'bg-yellow-100 text-yellow-800',
  normal: 'bg-green-100 text-green-800'
}

export default function StatusBadge({ status }) {
  return <span className={`px-2 py-1 rounded text-xs ${map[status] || 'bg-gray-100 text-gray-800'}`}>{status}</span>
}
