import React from 'react'

export default function EmptyState({ title = 'No data', subtitle }) {
  return (
    <div className="text-center p-8 text-gray-500">
      <div className="text-lg font-semibold">{title}</div>
      {subtitle && <div className="text-sm mt-2">{subtitle}</div>}
    </div>
  )
}
