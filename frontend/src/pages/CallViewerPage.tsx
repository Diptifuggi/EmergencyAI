// @ts-nocheck
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Badge,
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from '@/components/ui'
import { getEmergency } from '@/api/emergencyApi'
import { analysisForCall, categoryForCall, transcriptForCall } from '@/types/emergency'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

export default function CallViewerPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: emergency, isLoading, error } = useQuery({
    queryKey: ['emergency-call', id],
    queryFn: () => getEmergency(id as string),
    enabled: Boolean(id),
    refetchInterval: 15000,
  })

  if (isLoading) return <Loading />
  if (error || !emergency) return <ErrorMessage error={error || new Error('Emergency call not found.')} />

  const analysis = analysisForCall(emergency)
  const metadata = emergency.client_metadata || {}
  const helpRequired = Array.isArray(analysis.help_required) ? analysis.help_required : []
  const recommendation = analysis.dispatch_recommendation || {}
  const recommendedUnits = Array.isArray(recommendation.recommended_units) ? recommendation.recommended_units : []
  const emergencyNumbers = recommendation.emergency_numbers && typeof recommendation.emergency_numbers === 'object'
    ? recommendation.emergency_numbers
    : {}
  const transcript = transcriptForCall(emergency)
  const rawTranscript = emergency.text_content && emergency.text_content.trim() ? emergency.text_content : (transcript || 'Not available')
  const latitude = emergency.latitude ?? emergency.location?.latitude ?? null
  const longitude = emergency.longitude ?? emergency.location?.longitude ?? null
  const timestamp = emergency.created_at ? new Date(emergency.created_at) : null
  const updatedAt = emergency.updated_at ? new Date(emergency.updated_at) : null
  const callDate = timestamp && !Number.isNaN(timestamp.getTime())
    ? timestamp.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).replaceAll(',', '')
    : 'Not available'
  const callClock = timestamp && !Number.isNaN(timestamp.getTime())
    ? timestamp.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false })
    : 'Not available'
  const city = typeof metadata.city === 'string' && metadata.city.trim() ? metadata.city : 'Not available'
  const state = typeof metadata.state === 'string' && metadata.state.trim() ? metadata.state : 'Not available'
  const keywords = Array.isArray(analysis.emergency_keywords) ? analysis.emergency_keywords : []
  const audioEvents = Array.isArray((emergency as any)?.audio_events) ? (emergency as any).audio_events : []
  const dispatches = recommendedUnits.length > 0
    ? recommendedUnits.map((unit: string) => ({
        department: unit,
        officer: 'Recommendation only',
        status: recommendation.reason || 'Recommendation only',
      }))
    : []
  const locationDisplay = [emergency.location_address || metadata.location_address, city, state].filter((value) => typeof value === 'string' && value.trim()).join(', ')
  const call = {
    id: emergency.id,
    caller_name: typeof metadata.caller_name === 'string' && metadata.caller_name.trim() ? metadata.caller_name : 'Not available',
    caller_phone: typeof metadata.caller_phone === 'string' && metadata.caller_phone.trim() ? metadata.caller_phone : 'Not available',
    caller_email: typeof metadata.caller_email === 'string' && metadata.caller_email.trim() ? metadata.caller_email : 'Not available',
    age: metadata.age ?? 'Not available',
    gender: typeof metadata.gender === 'string' && metadata.gender.trim() ? metadata.gender : 'Not available',
    language: emergency.language || emergency.requested_language || 'Not available',
    source: emergency.source || 'Not available',
    call_type: emergency.call_type || 'Not available',
    status: emergency.status || 'Not available',
    priority: (analysis.priority_level || emergency.priority || 'Not available').toString(),
    category: categoryForCall(emergency),
    address: emergency.location_address || locationDisplay || 'Not available',
    city,
    state,
    latitude,
    longitude,
    call_date: callDate,
    call_clock: callClock,
    updated_at: updatedAt && !Number.isNaN(updatedAt.getTime()) ? updatedAt.toLocaleString('en-GB') : 'Not available',
    duration: 'Not available',
    severity_score: typeof analysis.priority_score === 'number' ? analysis.priority_score : null,
    emotion: analysis.panic_level ? `Panic (${analysis.panic_level})` : 'Not available',
    emotion_score: typeof analysis.panic_score === 'number' ? analysis.panic_score / 100 : null,
    background_noise: 'Not available',
    noise_level: 'Not available',
    vehicle_count: analysis.road_accident ? 'Road accident' : 'Not available',
    injured_people: typeof analysis.victim_count === 'number' ? String(analysis.victim_count) : 'Not available',
    fatalities: 'Not available',
    ambulance_required: helpRequired.length > 0 ? helpRequired.some((item) => String(item).toLowerCase().includes('ambulance') || String(item).toLowerCase().includes('medical')) : null,
    police_required: typeof analysis.police_required === 'boolean' ? analysis.police_required : helpRequired.some((item) => String(item).toLowerCase().includes('police')),
    fire_required: helpRequired.some((item) => String(item).toLowerCase().includes('fire')),
    incident_id: null,
    transcript_raw: rawTranscript,
    transcript_clean: transcript || 'Not available',
    keywords,
    audio_events: audioEvents,
    audio_url: emergency.audio_url || null,
    map_snapshot_url: emergency.map_snapshot_url || null,
    score_breakdown: {
      category: analysis.emergency_type || 'Not available',
      keywords: keywords.length ? keywords.join(', ') : 'Not available',
      emotion: typeof analysis.panic_score === 'number' ? analysis.panic_score : 'Not available',
      audio: emergency.audio_file_size ? `${emergency.audio_file_size} bytes` : 'Not available',
      location: latitude != null && longitude != null ? `${latitude.toFixed(5)}, ${longitude.toFixed(5)}` : 'Not available',
    },
    dispatches,
    emergency_numbers: emergencyNumbers,
  }
  const scoreRows = [
    { label: 'Category', value: call.score_breakdown.category ?? 'Not available' },
    { label: 'Keywords', value: call.score_breakdown.keywords ?? 'Not available' },
    { label: 'Emotion', value: call.score_breakdown.emotion ?? 'Not available' },
    { label: 'Audio', value: call.score_breakdown.audio ?? 'Not available' },
    { label: 'Location', value: call.score_breakdown.location ?? 'Not available' },
  ]
  const hasLocation = latitude != null && longitude != null

  const handleDownloadReport = () => {
    const content = `Emergency Call Report\n\nCall ID: ${call.id}\nCaller: ${call.caller_name}\nPhone: ${call.caller_phone}\nEmail: ${call.caller_email}\nStatus: ${call.status}\nPriority: ${call.priority}\nCategory: ${call.category}\n\nTranscript:\n${call.transcript_clean}\n`
    const blob = new Blob([content], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'Incident Report.pdf'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-4">
      <div className="mb-4 flex flex-wrap items-center gap-2 text-sm text-zinc-500">
        <button onClick={() => navigate('/calls')} className="text-blue-600 hover:underline">← Back to Live Calls</button>
        <span>•</span>
        <div>Emergency Call Investigation</div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[360px_1fr_320px]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Call Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-sm text-zinc-500">Call ID</div>
              <div className="font-semibold text-lg">{call.id}</div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-zinc-500">Caller</div>
                  <div className="font-medium">{call.caller_name}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Phone</div>
                  <div className="font-medium">{call.caller_phone}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Email</div>
                  <div className="font-medium">{call.caller_email}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Language</div>
                  <div className="font-medium">{call.language}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Age</div>
                  <div className="font-medium">{call.age}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Gender</div>
                  <div className="font-medium">{call.gender}</div>
                </div>
              </div>

              <div className="space-y-3 text-sm">
                <div>
                  <div className="text-zinc-500">Address</div>
                  <div className="font-medium">{[call.address, call.city, call.state].filter((part) => typeof part === 'string' && part && part !== 'Not available').join(', ') || 'Not available'}</div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-zinc-500">Date</div>
                    <div className="font-medium">{call.call_date}</div>
                  </div>
                  <div>
                    <div className="text-zinc-500">Time</div>
                    <div className="font-medium">{call.call_clock}</div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-zinc-500">Duration</div>
                    <div className="font-medium">{call.duration}</div>
                  </div>
                  <div>
                    <div className="text-zinc-500">Incident</div>
                    {call.incident_id ? <button onClick={() => navigate(`/incidents/${call.incident_id}`)} className="text-sm text-blue-600 hover:underline">{call.incident_id}</button> : <div className="font-medium">Not available</div>}
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <Badge className="bg-red-500 text-white">{call.priority}</Badge>
                <Badge className="bg-slate-800 text-white">{call.status}</Badge>
                <Badge className="bg-zinc-100 text-zinc-700">{call.category}</Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Call Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-zinc-600">
              <div><strong>Vehicles involved:</strong> {call.vehicle_count}</div>
              <div><strong>Injured people:</strong> {call.injured_people}</div>
              <div><strong>Fatalities:</strong> {call.fatalities}</div>
              <div><strong>Ambulance required:</strong> {call.ambulance_required == null ? 'Not available' : call.ambulance_required ? 'Yes' : 'No'}</div>
              <div><strong>Police required:</strong> {call.police_required == null ? 'Not available' : call.police_required ? 'Yes' : 'No'}</div>
              <div><strong>Fire required:</strong> {call.fire_required == null ? 'Not available' : call.fire_required ? 'Yes' : 'No'}</div>
              <div><strong>Noise level:</strong> {call.noise_level}</div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Transcript & Analysis</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div>
                <div className="text-sm text-zinc-500">Raw Transcript</div>
                <div className="mt-2 rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-sm leading-6 whitespace-pre-wrap">{call.transcript_raw}</div>
              </div>
              <div>
                <div className="text-sm text-zinc-500">Clean Transcript</div>
                <div className="mt-2 rounded-lg border border-zinc-200 bg-white p-4 text-sm leading-6 whitespace-pre-wrap">{call.transcript_clean}</div>
              </div>
              <div>
                <div className="text-sm text-zinc-500">Detected Keywords</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {Array.isArray(call.keywords) && call.keywords.length > 0 ? call.keywords.map((keyword) => (
                    <Badge key={keyword} className="bg-zinc-900 text-white">{keyword}</Badge>
                  )) : <span className="text-sm text-zinc-500">Not available</span>}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-zinc-500">Emotion</div>
                  <div className="font-medium">{call.emotion}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Emotion Score</div>
                  <div className="font-medium">{call.emotion_score == null ? 'Not available' : `${(call.emotion_score * 100).toFixed(0)}%`}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Background Noise</div>
                  <div className="font-medium">{call.background_noise}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Noise Level</div>
                  <div className="font-medium">{call.noise_level}</div>
                </div>
              </div>
              <div>
                <div className="text-sm font-medium mb-3">Audio Events</div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Event</TableHead>
                      <TableHead>Confidence</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Array.isArray(call.audio_events) && call.audio_events.length > 0 ? call.audio_events.map((event) => (
                      <TableRow key={event.event}>
                        <TableCell>{event.event}</TableCell>
                        <TableCell>{event.confidence}%</TableCell>
                      </TableRow>
                    )) : <TableRow><TableCell>Not available</TableCell><TableCell>Not available</TableCell></TableRow>}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>

        <aside className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Severity Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-center">
                <div className="text-5xl font-extrabold text-zinc-900">{call.severity_score ?? 'Not available'}</div>
                <div className="text-sm text-zinc-500">/ 100</div>
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                <Badge className="bg-red-500 text-white">{call.priority}</Badge>
                <Badge className="bg-slate-800 text-white">{call.status}</Badge>
              </div>
              <div>
                <div className="text-sm font-medium mb-2">Score Breakdown</div>
                <div className="space-y-2">
                  {scoreRows.map((row) => (
                    <div key={row.label} className="flex items-center justify-between text-sm">
                      <span>{row.label}</span>
                      <span className="font-semibold">{row.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Dispatch Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-zinc-600">
              {Array.isArray(call.dispatches) && call.dispatches.length > 0 ? call.dispatches.map((dispatch) => (
                <div key={dispatch.department} className="rounded-lg border border-zinc-200 p-3">
                  <div className="font-medium">{dispatch.department}</div>
                  <div>{dispatch.officer}</div>
                  <div className="mt-1"><Badge className="bg-slate-800 text-white">{dispatch.status}</Badge></div>
                </div>
              )) : <div className="text-sm text-zinc-500">No dispatch data returned by the backend.</div>}
            </CardContent>
          </Card>
        </aside>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Caller Location</CardTitle>
          </CardHeader>
          <CardContent>
            {hasLocation ? <div className="h-72 rounded-xl overflow-hidden border border-zinc-200">
              <MapContainer center={[call.latitude, call.longitude]} zoom={14} style={{ height: '100%', width: '100%' }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <Marker position={[call.latitude, call.longitude]}>
                  <Popup>Caller Location<br />{call.address}</Popup>
                </Marker>
              </MapContainer>
            </div> : <div className="h-72 rounded-xl overflow-hidden border border-zinc-200 flex items-center justify-center text-sm text-zinc-500">No location data</div>}
            <div className="mt-3 text-sm text-zinc-500">Caller Location • {call.address}{hasLocation ? ` (${call.latitude}, ${call.longitude})` : ''}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Action Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm text-zinc-600">Use these actions to manage the investigation workflow. All buttons are placeholder actions for the current demo.</div>
            <div className="grid gap-2">
              <Button onClick={() => call.caller_phone !== 'Not available' && window.open(`tel:${call.caller_phone.replace(/\s/g, '')}`)}>Call Back</Button>
              <Button variant="outline" onClick={handleDownloadReport}>Download Report</Button>
              <Button variant="outline" onClick={() => window.print()}>Print Report</Button>
              <Button variant="outline" onClick={() => call.audio_url && void new Audio(call.audio_url).play()}>Play Audio</Button>
              <Button variant="outline" onClick={() => navigate('/calls')}>Close Call</Button>
              <Button variant="outline" onClick={() => {}} >Transfer</Button>
              <Button variant="outline" onClick={() => {}} >Dispatch Again</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
