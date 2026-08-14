// @ts-nocheck
import React from 'react'

export default function PageContainer({ children, title }) {
  return (
    <div style={{marginLeft: 'var(--sidebar-width)'}} className="p-6">
      {title && <h1 className="text-2xl font-bold mb-4">{title}</h1>}
      <div>{children}</div>
    </div>
  )
}
