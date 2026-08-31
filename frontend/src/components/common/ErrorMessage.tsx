// @ts-nocheck
import React from 'react'

export default function ErrorMessage({ error }) {
  return (
    <div role="alert" className="p-4 bg-red-50 text-red-800 rounded">
      <strong>Error:</strong> {error?.message || 'An unexpected error occurred.'}
    </div>
  )
}
