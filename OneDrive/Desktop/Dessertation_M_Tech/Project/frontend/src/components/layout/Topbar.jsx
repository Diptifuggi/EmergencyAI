import React from 'react'
import { Search } from 'lucide-react'

function Clock() {
  const [now, setNow] = React.useState(new Date())
  React.useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return <div className="text-xs muted">{now.toLocaleString()}</div>
}

export default function Topbar() {
  return (
    <header className="flex items-center justify-between px-6 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
      <div className="flex items-center gap-4">
        <div className="relative">
          <input className="pl-9 pr-3 py-2 rounded bg-[rgba(255,255,255,0.03)] text-sm" placeholder="Global search (calls, incidents, resources)" />
          <Search className="absolute left-2 top-2 w-4 h-4 muted" />
        </div>
        <div className="px-3 py-1 rounded card">Live Incidents: <span className="font-semibold">0</span></div>
        <div className="px-3 py-1 rounded card">Critical Alerts: <span className="font-semibold">0</span></div>
      </div>

      <div className="flex items-center gap-4">
        <Clock />
        <div className="flex items-center gap-2">
          <div className="text-sm">Dispatcher</div>
          <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">D</div>
        </div>
      </div>
    </header>
  )
}
