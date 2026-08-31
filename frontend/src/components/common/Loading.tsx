// @ts-nocheck
import React from 'react'

export default function Loading({ label = 'Loading...' }) {
  return (
    <div role="status" aria-live="polite" className="p-4">
      <div className="text-sm text-muted-foreground">{label}</div>
    </div>
  )
}
