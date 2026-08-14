import React from 'react'
import { NavLink } from 'react-router-dom'
import { Home, Phone, AlertTriangle, Shuffle, BarChart2, Users, Settings } from 'lucide-react'

const items = [
  { to: '/dashboard', label: 'Dashboard', icon: Home },
  { to: '/calls', label: 'Emergency Calls', icon: Phone },
  { to: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { to: '/dispatch', label: 'Dispatch Center', icon: Shuffle },
  { to: '/analytics', label: 'Analytics', icon: BarChart2 },
  { to: '/users', label: 'Users', icon: Users },
  { to: '/settings', label: 'Settings', icon: Settings }
]

export default function Sidebar() {
  return (
    <div className="p-6 h-full text-sm">
      <div className="mb-6">
        <div className="text-xl font-bold tracking-widest">EmergencyIQ</div>
        <div className="text-xs muted">Command Center</div>
      </div>
      <nav className="flex flex-col gap-1">
        {items.map((it) => (
          <NavLink key={it.to} to={it.to} className={({ isActive }) => `flex items-center gap-3 p-3 rounded-md transition-all duration-200 ${isActive ? 'border-l-4 border-white bg-[rgba(255,255,255,0.03)]' : 'hover:bg-[rgba(255,255,255,0.02)]'}`}>
            <it.icon className="w-4 h-4" />
            <span className="truncate">{it.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
