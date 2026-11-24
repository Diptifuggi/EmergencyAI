// @ts-nocheck
import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import { getIncident } from '@/api/incidentsApi'
import { DEPARTMENTS } from '@/lib/constants'
import { normalizeIncidentRecord } from '@/lib/emergencyCallNormalizer'
import CallerLocationMap from '@/components/CallerLocationMap'
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
  const [dept, setDept] = useState(DEPARTMENTS[0] || '')
  const [officer, setOfficer] = useState('')
    const { data: incident, isLoading, error } = useQuery({
    queryKey: ['incident', id],
    queryFn: () => getIncident(id as string),
    enabled: Boolean(id),
  })
  const normalizedIncident = incident ? normalizeIncidentRecord(incident) : null
  const related = { data: [] }
  const dispatches: any[] = []
  const timeline: any[] = []
  const submitDispatch = () => toast.error('Dispatch records are not available from the current backend.')

  if (error) return <div className="p-4 text-sm text-red-600">Unable to load this incident from the backend.</div>

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
                      <div className="text-xl font-semibold truncate">{normalizedIncident?.title || 'Untitled'}</div>
                      <div className="text-sm text-gray-500">{normalizedIncident?.category || 'Not reported'}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold">{normalizedIncident?.severityScore ?? normalizedIncident?.severityLabel ?? 'Not reported'}</div>
                      <div className="text-sm">{normalizedIncident?.priority || 'Not reported'}</div>
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
                <div className="text-sm text-gray-500 mb-2">No related-call correlation data is available from the backend.</div>
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
                  <div className="text-4xl font-extrabold">
                    {normalizedIncident?.severityScore != null
                      ? `${normalizedIncident.severityScore} / 100`
                      : normalizedIncident?.severityLabel || 'Not reported'}
                  </div>
                  <div className="mt-2">Priority: {normalizedIncident?.priority || 'Not reported'}</div>
                  <div className="mt-1 text-sm text-gray-500">Calls: {normalizedIncident?.callCount ?? 'Not reported'}</div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Active Dispatches</CardTitle></CardHeader>
            <CardContent>
              {dispatches.length === 0 ? <div>No dispatch data available from the backend.</div> : (
                <div>
                  {dispatches.map((d, index) => (
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
                {timeline.map((ev, i) => (
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
              <CallerLocationMap
                latitude={normalizedIncident?.latitude ?? null}
                longitude={normalizedIncident?.longitude ?? null}
                accuracy={normalizedIncident?.locationAccuracy ?? null}
                address={normalizedIncident?.locationAddress ?? null}
                addressStatus={normalizedIncident?.locationAddressStatus ?? 'unavailable'}
                status={normalizedIncident?.locationStatus ?? null}
                capturedAt={normalizedIncident?.locationTimestamp ?? null}
                coordinateStatus={normalizedIncident?.locationCoordinatesStatus ?? 'missing'}
                coordinatesConflict={normalizedIncident?.locationCoordinatesConflict ?? false}
                snapshotAvailable={normalizedIncident?.mapSnapshotAvailable ?? false}
                snapshotUrl={normalizedIncident?.mapSnapshotUrl ?? null}
                label="Reported incident location"
              />
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
                <div className="flex space-x-2"><Button onClick={submitDispatch}>Dispatch</Button><Button variant="secondary" onClick={()=>navigate('/incidents')}>Close</Button></div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  )
}
