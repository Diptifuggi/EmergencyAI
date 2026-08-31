// @ts-nocheck
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

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

  const MOCK_INCIDENTS = [
    {
      id: 'INC-001',
      title: 'Multi-vehicle collision Silvassa Main Road',
      incident_type: 'Road Accident',
      severity: 92,
      priority: 'Critical',
      priority_color: 'text-red-600',
      status: 'Open',
      call_count: 5,
      latitude: 20.2766,
      longitude: 73.0144,
      created_at: '26 Jun 2026, 09:12',
    },
    {
      id: 'INC-002',
      title: 'Building fire GIDC Industrial Area',
      incident_type: 'Fire',
      severity: 85,
      priority: 'Very High',
      priority_color: 'text-orange-600',
      status: 'Assigned',
      call_count: 8,
      latitude: 20.3689,
      longitude: 72.9017,
      created_at: '26 Jun 2026, 08:47',
    },
    {
      id: 'INC-003',
      title: 'Medical emergency Vapi Hospital Road',
      incident_type: 'Medical Emergency',
      severity: 78,
      priority: 'Very High',
      priority_color: 'text-orange-600',
      status: 'Open',
      call_count: 3,
      latitude: 20.3714,
      longitude: 72.9084,
      created_at: '26 Jun 2026, 08:31',
    },
    {
      id: 'INC-004',
      title: 'Women safety incident near railway station',
      incident_type: 'Women Safety',
      severity: 71,
      priority: 'High',
      priority_color: 'text-amber-600',
      status: 'In Progress',
      call_count: 2,
      latitude: 20.6,
      longitude: 72.93,
      created_at: '26 Jun 2026, 08:15',
    },
    {
      id: 'INC-005',
      title: 'Flash flood NH48 underpass',
      incident_type: 'Natural Disaster',
      severity: 80,
      priority: 'Very High',
      priority_color: 'text-orange-600',
      status: 'Open',
      call_count: 11,
      latitude: 20.1809,
      longitude: 72.9631,
      created_at: '26 Jun 2026, 07:58',
    },
    {
      id: 'INC-006',
      title: 'Child abuse report Dadra sector',
      incident_type: 'Child Abuse',
      severity: 68,
      priority: 'High',
      priority_color: 'text-amber-600',
      status: 'Assigned',
      call_count: 1,
      latitude: 20.2994,
      longitude: 72.973,
      created_at: '26 Jun 2026, 07:32',
    },
    {
      id: 'INC-007',
      title: 'Cyber fraud complaint Vapi city',
      incident_type: 'Cyber Crime',
      severity: 35,
      priority: 'Low',
      priority_color: 'text-blue-600',
      status: 'Resolved',
      call_count: 1,
      latitude: 20.3716,
      longitude: 72.9029,
      created_at: '26 Jun 2026, 07:10',
    },
    {
      id: 'INC-008',
      title: 'Gas cylinder explosion residential area',
      incident_type: 'Fire',
      severity: 88,
      priority: 'Critical',
      priority_color: 'text-red-600',
      status: 'Open',
      call_count: 6,
      latitude: 20.27,
      longitude: 73.02,
      created_at: '26 Jun 2026, 06:55',
    },
  ]

  const incidents = MOCK_INCIDENTS
  const isLoading = false
  const refetch = async () => {}

  const active = incidents.find((i: any) => i.id === selectedId) || incidents[0] || null

  return (
    <div className="min-h-screen grid grid-cols-[340px_1fr]">
      <aside className="bg-white border-r overflow-auto h-screen sticky top-0">
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Incidents</h2>
            <div className="px-2 py-1 bg-gray-200 rounded text-sm">{MOCK_INCIDENTS.length}</div>
          </div>

          <div className="mb-3">
            <div className="flex space-x-2">
              {['All','Open','Assigned','Resolved'].map((s: any) => (
                <button key={s} onClick={() => setActiveTab(s)} className={`px-3 py-1 rounded ${activeTab===s? 'bg-zinc-900 text-white' : ''}`}>{s}</button>
              ))}
            </div>
          </div>

          <div className="mb-3">
            <input placeholder="Search title, category, location" className="w-full p-2 border rounded" />
          </div>

          <div className="space-y-2">
            {isLoading ? (
              new Array(8).fill(0).map((_, i) => (
                <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
              ))
            ) : (
              incidents
                .filter((it: any) => (activeTab === 'All' ? true : it.status === activeTab))
                .filter((it: any) => it.latitude !== null && it.longitude !== null)
                .map((inc: any) => {
                const priority = inc.priority || 'Low'
                const colorClass = priority === 'Critical' ? 'bg-red-600' : priority === 'Very High' ? 'bg-orange-500' : priority === 'High' ? 'bg-amber-500' : priority === 'Moderate' ? 'bg-green-500' : 'bg-blue-500'
                return (
                  <div key={inc.id} onClick={() => { setSelectedId(inc.id); setSelectedPos([inc.latitude, inc.longitude]); navigate(`/incidents/${inc.id}`) }} className={`flex items-center p-2 rounded hover:bg-gray-50 cursor-pointer ${selectedId === inc.id ? 'bg-zinc-50 border-r-2 border-r-zinc-900' : ''}`}>
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
          {incidents
            .filter((it: any) => (activeTab === 'All' ? true : it.status === activeTab))
            .filter((it: any) => it.latitude !== null && it.longitude !== null)
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
