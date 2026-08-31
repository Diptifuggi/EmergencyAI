import React from 'react'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function DashboardLayout({ children }) {
  return (
    <div className="min-h-screen flex">
      <aside className="w-64 dark-sidebar text-white hidden md:block"> 
        <Sidebar />
      </aside>
      <div className="flex-1 min-h-screen bg-white">
        <Topbar />
        <main className="p-6">{children}</main>
      </div>
    </div>
  )
}
