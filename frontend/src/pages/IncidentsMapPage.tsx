// @ts-nocheck
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { listIncidents } from '@/api/incidentsApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'

// Fix default icon paths for Leaflet in many bundlers
delete (L as any).Icon.Default.prototype._getIconUrl
;(L as any).Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const INDIA_CENTER = [20.5937, 78.9629]

function createPriorityMarker(priority: any) {
  const color = priority === 'Critical' ? '#dc2626' : priority === 'Very High' ? '#f97316' : priority === 'High' ? '#f59e0b' : priority === 'Moderate' ? '#16a34a' : '#3b82f6'
  const html = `
    <div style="display:flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.3);background:${color};border:2px solid #fff"></div>
  `
  return (L as any).divIcon({ html, className: '', iconSize: [40, 40], iconAnchor: [20, 40], popupAnchor: [0, -40] })
}

function FlyToMarker({ position }: any) {
  const map = useMap()
  if (position) {
    map.flyTo(position, 12, { duration: 0.8 })
  }
  return null
}

export default function IncidentsMapPage() {
  const navigate = useNavigate()
  const [selectedId, setSelectedId] = React.useState<any>(null)
  const [selectedPos, setSelectedPos] = React.useState<any>(null)
  const [activeTab, setActiveTab] = React.useState('All')
  const [searchText, setSearchText] = React.useState('')
  const { data: backendIncidents = [], isLoading, error } = useQuery({
    queryKey: ['incidents'],
    queryFn: () => listIncidents(),
    refetchInterval: 15000,
    staleTime: 5000,
  })
  const incidents = backendIncidents.map((incident: any) => ({
    id: incident.id,
    title: incident.title || 'Not available',
    incident_type: incident.incident_type || incident.category || 'Emergency',
    severity: incident.severity ?? '—',
    priority: incident.priority || 'Moderate',
    priority_color: incident.priority === 'Critical' ? 'text-red-600' : incident.priority === 'High' ? 'text-amber-500' : 'text-zinc-500',
    status: incident.status || 'Open',
    call_count: incident.call_count ?? 1,
    latitude: typeof incident.latitude === 'number' && !isNaN(incident.latitude) ? incident.latitude : null,
    longitude: typeof incident.longitude === 'number' && !isNaN(incident.longitude) ? incident.longitude : null,
    created_at: incident.created_at ? new Date(incident.created_at).toLocaleString() : 'Not available',
  }))
  const visibleIncidents = incidents
    .filter((item) => activeTab === 'All' || (activeTab === 'Open' ? item.status === 'Open' : item.status === activeTab))
    .filter((item) => `${item.title} ${item.incident_type} ${item.id}`.toLowerCase().includes(searchText.toLowerCase()))

  if (error) return <ErrorMessage error={error} />

  return (
    <div className="min-h-screen grid grid-cols-[340px_1fr]">
      <aside className="bg-white border-r overflow-auto h-screen sticky top-0">
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Incidents</h2>
            <div className="px-2 py-1 bg-gray-200 rounded text-sm">{incidents.length}</div>
          </div>

          <div className="mb-3">
            <div className="flex space-x-2">
              {['All','Open','Assigned','Resolved'].map((s: any) => (
                <button key={s} onClick={() => setActiveTab(s)} className={`px-3 py-1 rounded ${activeTab===s? 'bg-zinc-900 text-white' : ''}`}>{s}</button>
              ))}
            </div>
          </div>

          <div className="mb-3">
            <input placeholder="Search title, category, location" className="w-full p-2 border rounded" value={searchText} onChange={(event) => setSearchText(event.target.value)} />
          </div>

          <div className="space-y-2">
            {isLoading ? (
              new Array(8).fill(0).map((_, i) => (
                <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
              ))
            ) : (
              visibleIncidents
                .map((inc: any) => {
                const priority = inc.priority || 'Low'
                const colorClass = priority === 'Critical' ? 'bg-red-600' : priority === 'Very High' ? 'bg-orange-500' : priority === 'High' ? 'bg-amber-500' : priority === 'Moderate' ? 'bg-green-500' : 'bg-blue-500'
                return (
                  <div key={inc.id} onClick={() => { setSelectedId(inc.id); if (inc.latitude !== null && inc.longitude !== null) { setSelectedPos([inc.latitude, inc.longitude]); } navigate(`/incidents/${inc.id}`) }} className={`flex items-center p-2 rounded hover:bg-gray-50 cursor-pointer ${selectedId === inc.id ? 'bg-zinc-50 border-r-2 border-r-zinc-900' : ''}`}>
                    <div style={{ width: 8, height: 32, background: colorClass }} className="mr-3 rounded-sm" />
                    <div className="flex-1 min-w-0">
                      <div className="truncate font-semibold text-sm">{inc.title}</div>
                      <div className="text-xs text-zinc-500">{inc.call_count} calls • {inc.incident_type}</div>
                      <div className="text-xs text-zinc-400">{inc.created_at}</div>
                    </div>
                    <div className="text-right ml-3">
                      <div className="text-lg font-bold">{inc.severity}</div>
                      <div className={`text-xs font-medium ${inc.priority_color}`}>{inc.priority}</div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </aside>

      <main className="h-screen">
        <MapContainer center={INDIA_CENTER} zoom={5} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {visibleIncidents
            .filter((inc: any) => inc.latitude !== null && inc.longitude !== null && !isNaN(inc.latitude) && !isNaN(inc.longitude))
            .map((inc: any) => (
            <Marker key={inc.id} position={[inc.latitude, inc.longitude]} icon={createPriorityMarker(inc.priority)} eventHandlers={{ click: (e: any) => { const map = e.target._map; map.flyTo([inc.latitude, inc.longitude], 12); setSelectedId(inc.id); setSelectedPos([inc.latitude, inc.longitude]) } }}>
              <Popup>
                <div className="w-64">
                  <div className="font-medium truncate">{inc.title}</div>
                  <div className="text-sm text-gray-600">{inc.incident_type}</div>
                  <div className="mt-2">Calls: {inc.call_count}</div>
                  <div className="mt-2">Severity: {inc.severity}</div>
                  <div className="mt-3"><button onClick={() => navigate(`/incidents/${inc.id}`)} className="px-3 py-1 bg-zinc-900 text-white rounded">View Incident</button></div>
                </div>
              </Popup>
            </Marker>
          ))}
          {selectedPos ? <FlyToMarker position={selectedPos} /> : null}
        </MapContainer>
      </main>
    </div>
  )
}
