// @ts-nocheck
import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import axiosClient from '@/api/axiosClient'
import { MapContainer, TileLayer, Marker } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({ iconRetinaUrl: markerIcon2x, iconUrl: markerIcon, shadowUrl: markerShadow })

import { SOP_ACTIONS, DEPARTMENTS } from '@/lib/constants'
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Textarea,
  Input,
  Select,
  Skeleton,
} from '@/components/ui'

export default function IncidentDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [dept, setDept] = useState(DEPARTMENTS[0] || '')
  const [officer, setOfficer] = useState('')

  // TODO: Replace with real API when backend ready
  const MOCK_INCIDENT_DETAIL = {
    id: 'INC-001',
    title: 'Multi-vehicle collision Silvassa Main Road',
    incident_type: 'Road Accident',
    severity: 92,
    priority: 'Critical',
    call_count: 5,
    status: 'Open',
    created_at: '26 Jun 2026, 09:12',
    clustered_calls: [
      {
        id: 'C001', caller: 'Caller 1',
        received: '26 Jun 2026, 09:18',
        similarity: 0.95, similarity_width: '95%',
        similarity_label: 'Very similar',
        priority: 'Critical', priority_color: 'text-red-600',
        transcript: 'Major accident on Silvassa Main Road near bus stand, three people unconscious heavy bleeding',
      },
      {
        id: 'C002', caller: 'Caller 2',
        received: '26 Jun 2026, 09:11',
        similarity: 0.88, similarity_width: '88%',
        similarity_label: 'Very similar',
        priority: 'Very High', priority_color: 'text-orange-600',
        transcript: 'Truck hit two bikes near Silvassa bus stand, people injured on road',
      },
      {
        id: 'C003', caller: 'Caller 3',
        received: '26 Jun 2026, 09:04',
        similarity: 0.82, similarity_width: '82%',
        similarity_label: 'Similar',
        priority: 'High', priority_color: 'text-amber-600',
        transcript: 'Accident Silvassa road, ambulance needed urgently, two lying on ground',
      },
      {
        id: 'C004', caller: 'Caller 4',
        received: '26 Jun 2026, 08:57',
        similarity: 0.79, similarity_width: '79%',
        similarity_label: 'Similar',
        priority: 'High', priority_color: 'text-amber-600',
        transcript: 'Road accident near main road bus stop, vehicle overturned',
      },
      {
        id: 'C005', caller: 'Caller 5',
        received: '26 Jun 2026, 08:50',
        similarity: 0.76, similarity_width: '76%',
        similarity_label: 'Similar',
        priority: 'Moderate', priority_color: 'text-green-600',
        transcript: 'Collision on Silvassa highway, traffic blocked, people on road',
      },
    ],
    dispatches: [
      { department: 'Police', officer: 'Officer Rajesh K.', time: '26 Jun 2026, 09:20', status: 'Dispatched' },
      { department: 'Ambulance', officer: 'Unit 108-B', time: '26 Jun 2026, 09:22', status: 'En Route' },
    ],
    timeline: [
      { event: 'First Call Received', time: '26 Jun 2026, 08:50' },
      { event: 'Calls Correlated', time: '26 Jun 2026, 09:00' },
      { event: 'Incident Created', time: '26 Jun 2026, 09:05' },
      { event: 'Police Dispatched', time: '26 Jun 2026, 09:20' },
      { event: 'Ambulance Dispatched', time: '26 Jun 2026, 09:22' },
    ],
  }

  const incident = MOCK_INCIDENT_DETAIL
  const isLoading = false
  const related = { data: incident.clustered_calls }

  const dispatchMut = useMutation({ mutationFn: async (payload) => { await axiosClient.post(`/incidents/${id}/dispatch`, payload) }, onSuccess: () => qc.invalidateQueries({ queryKey: ['incident', id] }) })

  const similarityLabel = (v) => v >= 0.9 ? 'Very Similar' : v >= 0.75 ? 'Similar' : 'Possibly Related'
  const similarityClass = (v) => v >= 0.9 ? 'bg-zinc-900 text-white' : v >= 0.75 ? 'bg-zinc-600 text-white' : 'bg-zinc-400 text-black'

  return (
    <div className="p-4">
      <div className="flex items-center gap-2 mb-4 text-sm text-gray-600">
        <a href="/incidents">Incidents</a>
        <span>&gt;</span>
        <div>Incident #{id}</div>
      </div>

      <div className="grid grid-cols-[1fr_320px] gap-6">
        <div>
          <Card>
            <CardContent>
              {isLoading ? <Skeleton className="h-24" /> : (
                <div>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xl font-semibold truncate">{incident?.title || 'Untitled'}</div>
                      <div className="text-sm text-gray-500">{incident?.incident_type}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold">{incident?.severity ?? '—'}</div>
                      <div className="text-sm">{incident?.priority || '—'}</div>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="mt-4">
            <Card>
              <CardHeader><CardTitle>Related Emergency Calls</CardTitle></CardHeader>
              <CardContent>
                <div className="text-sm text-gray-500 mb-2">Grouped by semantic similarity using pgvector cosine distance (≥0.75 threshold)</div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Caller</TableHead>
                      <TableHead>Received</TableHead>
                      <TableHead>Similarity</TableHead>
                      <TableHead>Priority</TableHead>
                      <TableHead>Transcript</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(related.data || []).map((call) => (
                      <TableRow key={call.id}>
                        <TableCell>{call.caller}</TableCell>
                        <TableCell>{call.received}</TableCell>
                        <TableCell>
                          <div>
                            <span className="inline-block bg-zinc-800 text-white text-xs font-mono px-2 py-0.5 rounded mb-1">{call.similarity.toFixed(2)}</span>
                            <div className="w-24 h-1.5 bg-zinc-200 rounded-full">
                              <div className="h-1.5 bg-zinc-800 rounded-full" style={{ width: call.similarity_width }} />
                            </div>
                            <span className="text-xs text-zinc-400">{call.similarity_label}</span>
                          </div>
                        </TableCell>
                        <TableCell className={`${call.priority_color} font-medium`}>{call.priority}</TableCell>
                        <TableCell>{call.transcript.length > 60 ? `${call.transcript.slice(0, 60)}...` : call.transcript}</TableCell>
                        <TableCell>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigate(`/calls/${call.id}`)}
                          >
                            View
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <div className="mt-4 bg-zinc-50 border border-zinc-200 p-4">
              <div className="flex items-start gap-3">
                <div className="text-2xl">ℹ️</div>
                <div>
                  <div className="font-semibold">How incident correlation works</div>
                  <div className="text-sm mt-2">Each transcript is converted to a 384-dimensional semantic vector using BAAI/bge-small-en-v1.5.
                  Calls are grouped when cosine similarity ≥ 0.75 AND received within 6 hours.
                  This identifies duplicate reports of the same incident automatically — a primary research contribution of EmergencyIQ.</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <aside className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Severity Summary</CardTitle></CardHeader>
            <CardContent>
              {isLoading ? <Skeleton className="h-24" /> : (
                <div className="text-center">
                  <div className="text-4xl font-extrabold">{incident?.severity ?? 0} / 100</div>
                  <div className="mt-2">Priority: {incident?.priority}</div>
                  <div className="mt-1 text-sm text-gray-500">Calls: {incident?.call_count ?? 0}</div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Active Dispatches</CardTitle></CardHeader>
            <CardContent>
              {(incident?.dispatches || []).length === 0 ? <div>No active dispatches</div> : (
                <div>
                  {(incident.dispatches || []).map((d, index) => (
                    <div key={index} className="flex items-start justify-between gap-4 py-3">
                      <div>
                        <div className="text-sm font-semibold">{d.department}</div>
                        <div className="text-sm text-zinc-500">{d.officer}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-zinc-400">{d.time}</div>
                        <div className={`text-xs font-medium ${d.status === 'En Route' ? 'text-emerald-600' : 'text-zinc-500'}`}>{d.status}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Incident Timeline</CardTitle></CardHeader>
            <CardContent>
              <div className="relative pl-4 border-l-2 border-zinc-200">
                {(incident?.timeline || []).map((ev, i) => (
                  <div key={i} className="relative mb-6">
                    <span className={`absolute -left-2 top-1 h-3 w-3 rounded-full ${i === 0 ? 'bg-zinc-900' : 'bg-zinc-300'}`} />
                    <div className="font-medium text-sm">{ev.event}</div>
                    <div className="text-xs text-zinc-400">{ev.time}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Mini Map</CardTitle></CardHeader>
            <CardContent>
              {incident?.latitude && incident?.longitude ? (
                <MapContainer center={[incident.latitude, incident.longitude]} zoom={13} style={{ height: 220, width: '100%' }}>
                  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  <Marker position={[incident.latitude, incident.longitude]} />
                </MapContainer>
              ) : <div>No location data</div>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Add Dispatch</CardTitle></CardHeader>
            <CardContent>
              <div className="mb-2">
                <label className="block text-sm">Department</label>
                <select value={dept} onChange={(e)=>setDept(e.target.value)} className="w-full p-2 border rounded">{DEPARTMENTS.map(d=>(<option key={d} value={d}>{d}</option>))}</select>
              </div>
              <div className="mb-2"><label className="block text-sm">Officer</label><input value={officer} onChange={(e)=>setOfficer(e.target.value)} className="w-full p-2 border rounded" /></div>
              <div className="flex space-x-2"><Button onClick={()=>dispatchMut.mutate({ department: dept, officer })}>Dispatch</Button><Button variant="secondary" onClick={()=>navigate('/incidents')}>Close</Button></div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  )
}
