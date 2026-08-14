// @ts-nocheck
import React from 'react'
import { NavLink } from 'react-router-dom'

export default function Sidebar() {
  const linkClass = ({ isActive }) =>
    `block px-3 py-2 rounded-md ${isActive ? 'bg-sidebar-active' : 'hover:bg-sidebar-hover'}`

  return (
    <aside className="sidebar fixed top-0 left-0 h-full p-4 flex flex-col" style={{width: 'var(--sidebar-width)', background: 'var(--sidebar-bg)'}}>
      <div className="mb-6">
        <h1 className="text-lg font-bold" style={{color: 'var(--sidebar-fg)'}}>EmergencyIQ</h1>
      </div>
      <nav className="flex-1">
        <ul className="space-y-2">
          <li><NavLink to="/" className={linkClass} style={{color: 'var(--sidebar-fg)'}}>Dashboard</NavLink></li>
          <li><NavLink to="/emergencies" className={linkClass} style={{color: 'var(--sidebar-fg)'}}>Emergency Calls</NavLink></li>
          <li><NavLink to="/dispatch" className={linkClass} style={{color: 'var(--sidebar-fg)'}}>Dispatch Center</NavLink></li>
          <li><NavLink to="/map" className={linkClass} style={{color: 'var(--sidebar-fg)'}}>Incident Map</NavLink></li>
          <li><NavLink to="/sop" className={linkClass} style={{color: 'var(--sidebar-fg)'}}>SOP Manager</NavLink></li>
          <li><NavLink to="/analytics" className={linkClass} style={{color: 'var(--sidebar-fg)'}}>Analytics</NavLink></li>
        </ul>
      </nav>
      <div className="mt-6 text-sm" style={{color: 'var(--sidebar-fg)'}}>v0.1</div>
    </aside>
  )
}
