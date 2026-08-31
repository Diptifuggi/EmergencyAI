import React from 'react'
import { NavLink } from 'react-router-dom'

const linkClass = ({ isActive }: { isActive: boolean }) => `block px-3 py-2 rounded-md ${isActive ? 'bg-sidebar-active' : ''}`

export default function Sidebar() {
  return (
    <aside className="sidebar fixed top-0 left-0 h-full p-4 flex flex-col" style={{width: 'var(--sidebar-width)'}}>
      <div className="mb-6">
        <h1 className="text-lg font-bold" style={{color: 'var(--sidebar-fg)'}}>EmergencyIQ</h1>
      </div>

      <nav className="flex-1">
        <ul className="space-y-2">
          <li>
            <NavLink to="/" className={(props) => linkClass(props)} style={{color: 'var(--sidebar-fg)'}}>Dashboard</NavLink>
          </li>
          <li>
            <NavLink to="/calls" className={(props) => linkClass(props)} style={{color: 'var(--sidebar-fg)'}}>Calls</NavLink>
          </li>
          <li>
            <NavLink to="/incidents" className={(props) => linkClass(props)} style={{color: 'var(--sidebar-fg)'}}>Incidents</NavLink>
          </li>
          <li>
            <NavLink to="/map" className={(props) => linkClass(props)} style={{color: 'var(--sidebar-fg)'}}>Map</NavLink>
          </li>
          <li>
            <NavLink to="/users" className={(props) => linkClass(props)} style={{color: 'var(--sidebar-fg)'}}>Users</NavLink>
          </li>
          <li>
            <NavLink to="/about" className={(props) => linkClass(props)} style={{color: 'var(--sidebar-fg)'}}>About</NavLink>
          </li>
        </ul>
      </nav>

      <div className="mt-6 text-sm" style={{color: 'var(--sidebar-fg)'}}>
        <div>v0.1</div>
      </div>
    </aside>
  )
}
