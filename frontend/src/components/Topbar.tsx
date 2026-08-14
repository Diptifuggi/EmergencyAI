import React from 'react'

export default function Topbar() {
  return (
    <header className="topbar fixed top-0 left-0 right-0 flex items-center px-4" style={{height: 'var(--topbar-height)', marginLeft: 'var(--sidebar-width)', borderBottom: '1px solid rgb(var(--sidebar-border))', background: 'white'}}>
      <div className="flex-1">
        <h2 className="text-sm font-medium">Emergency Operations</h2>
      </div>
      <div className="flex items-center gap-3">
          <button onClick={() => window.dispatchEvent(new CustomEvent('openNewCallDialog'))} className="bg-black text-white px-3 py-1 rounded text-sm">New Call</button>
          <button className="px-3 py-1 rounded text-sm" aria-label="profile">Ops</button>
      </div>
    </header>
  )
}
