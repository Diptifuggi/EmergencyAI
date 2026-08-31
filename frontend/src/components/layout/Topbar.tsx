// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Bell, Search, User, CheckCircle, Menu } from 'lucide-react'
import { Button } from '@/components/ui'
import { useQuery } from '@tanstack/react-query'
import { listCalls } from '@/api/callsApi'
import { getPriorityConfig } from '@/lib/priorityUtils'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

function useClock(){
  const [now, setNow] = useState(new Date())
  useEffect(()=>{
    const id = setInterval(()=> setNow(new Date()), 1000)
    return ()=> clearInterval(id)
  },[])
  return now
}

const PATH_TITLES = {
  '/dashboard': 'Dashboard',
  '/calls': 'Live Calls',
  '/incidents': 'Incidents',
  '/analytics': 'Analytics',
  '/admin/users': 'User Management',
  '/admin/roles': 'Roles',
  '/admin/audit': 'Audit Logs',
}

export default function Topbar(){
  const now = useClock()
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const [sheetOpen, setSheetOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)

  const title = PATH_TITLES[location.pathname] || 'Emergency Operations'

  const { data: critical } = useQuery({ queryKey: ['calls','critical'], queryFn: () => listCalls({ priority: 'Critical', page_size: 5 }), refetchInterval: 15000, retry: false })
  const criticalCount = critical?.length || 0

  function handleViewCall(id){ navigate(`/calls/${id}`); setSheetOpen(false) }

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center px-4">
      <div className="flex items-center w-1/3">
        <button className="p-2 mr-2 md:hidden" onClick={() => window.dispatchEvent(new CustomEvent('toggleMobileSidebar'))} aria-label="Open menu"><Menu className="w-5 h-5" /></button>
        <div className="text-sm font-medium">{title}</div>
      </div>

      <div className="flex-1 text-center">
        <div className="text-sm text-gray-600">{now.toLocaleDateString('en-GB', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' })}  |  {now.toLocaleTimeString('en-GB', { hour12: false })} IST</div>
      </div>

      <div className="w-1/3 flex items-center justify-end gap-4">
        <div className="mr-2">
          <Button onClick={() => window.dispatchEvent(new CustomEvent('openNewCallDialog'))} className="bg-black text-white">New Call</Button>
        </div>
        <div className="relative">
          <button onClick={()=> setSheetOpen(s => !s)} className="relative p-2 rounded hover:bg-gray-50">
            <Bell className="w-5 h-5" />
            {criticalCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-600 text-white text-xs rounded-full px-1.5">{criticalCount}</span>
            )}
          </button>

          {sheetOpen && (
            <div className="fixed right-4 top-16 z-50">
              <div className="w-[380px] bg-white border shadow-lg">
                <div className="p-4 border-b flex items-center justify-between">
                  <div className="font-semibold">Critical Alerts</div>
                  <button onClick={()=>setSheetOpen(false)} className="text-sm text-gray-500">Close</button>
                </div>
                <div className="p-3">
                  {(!critical || critical.length === 0) ? (
                    <div className="flex flex-col items-center justify-center py-8">
                      <div className="text-green-600 mb-3"><CheckCircle className="w-8 h-8" /></div>
                      <div className="font-medium">No active critical calls</div>
                    </div>
                  ) : (
                    <ul className="space-y-3">
                      {critical.slice(0,5).map(c => {
                        const cfg = getPriorityConfig(c.priority || 'Critical')
                        return (
                          <li key={c.id} className="flex items-center justify-between">
                            <div>
                              <div className="font-medium">{c.caller_name || c.caller || 'Unknown'}</div>
                              <div className="text-xs text-gray-500">{c.category || '—'} • Score: {c.score ?? '—'}</div>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="px-2 py-0.5 text-xs rounded" style={{ background: cfg.color + '20', color: cfg.color }}>{cfg.label}</div>
                              <button onClick={()=>handleViewCall(c.id)} className="text-sm text-blue-600">View</button>
                            </div>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        <div>
          <button onClick={()=> setSearchOpen(true)} className="p-2 rounded hover:bg-gray-50"><Search className="w-5 h-5" /></button>
          {searchOpen && (
            <div className="fixed inset-0 bg-black/40 z-40 flex items-start justify-center pt-24">
              <div className="bg-white w-[720px] p-4 rounded shadow">
                <div className="flex items-center gap-2">
                  <input autoFocus value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search calls by number or name" className="flex-1 border px-3 py-2 rounded" />
                  <button onClick={()=> setSearchOpen(false)} className="text-sm text-gray-600">Close</button>
                </div>
                <div className="mt-3">
                  {query.length < 3 ? <div className="text-sm text-gray-500">Type 3+ characters to search</div> : <SearchResults q={query} onView={(id)=>{navigate(`/calls/${id}`); setSearchOpen(false)}} />}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 relative">
          <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-sm">{(user?.full_name||'O').slice(0,1)}</div>
          <div className="relative">
            <button className="text-sm" onClick={()=> setMenuOpen(s=>!s)}>
              {user?.full_name || 'Operator'}
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-2 w-44 bg-white border shadow z-30">
                <button onClick={()=> { navigate('/profile'); setMenuOpen(false) }} className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50">My Profile</button>
                <button onClick={()=>{ logout(); navigate('/login') }} className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50">Logout</button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

function SearchResults({ q, onView }){
  const { data } = useQuery({ queryKey: ['search', q], queryFn: () => listCalls({ q, limit: 10 }), enabled: q.length >= 3, retry: false })
  if (!data) return <div className="text-sm text-gray-500">Searching…</div>
  if (data.length === 0) return <div className="text-sm text-gray-500">No results</div>
  return (
    <ul className="space-y-2">
      {data.map(d => (
        <li key={d.id} className="flex items-center justify-between">
          <div>
            <div className="font-medium">{d.caller_name || d.caller || 'Unknown'}</div>
            <div className="text-xs text-gray-500">{d.phone_number || d.source || ''}</div>
          </div>
          <div>
            <button onClick={()=> onView(d.id)} className="text-sm text-blue-600">View</button>
          </div>
        </li>
      ))}
    </ul>
  )
}
