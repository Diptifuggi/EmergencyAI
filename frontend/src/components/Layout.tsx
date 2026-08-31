import React from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />

      <div
        className="flex flex-col flex-1 overflow-hidden"
        style={{ marginLeft: 'var(--sidebar-width)' }}
      >
        <Topbar />

        <main
          className="flex-1 overflow-y-auto bg-gray-50 p-6"
          style={{ paddingTop: 'calc(var(--topbar-height) + 24px)' }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}
