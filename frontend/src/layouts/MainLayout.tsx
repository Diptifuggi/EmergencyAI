// @ts-nocheck
import React from 'react'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function MainLayout({ children }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="flex-1" style={{marginLeft: 'var(--sidebar-width)'}}>
        <Topbar />
        <main style={{paddingTop: 'var(--topbar-height)'}} className="content">
          {children}
        </main>
      </div>
    </div>
  )
}
