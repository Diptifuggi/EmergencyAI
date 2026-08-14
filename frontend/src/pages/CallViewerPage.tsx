// @ts-nocheck
import React from 'react'
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

// TODO Replace with FastAPI endpoint
const MOCK_CALL_DETAILS = {
  id: 'CALL-001',
  caller_name: 'Ramesh Patel',
  caller_phone: '+91 9876543210',
  caller_email: 'ramesh@gmail.com',
  age: 38,
  gender: 'Male',
  language: 'Gujarati',
  address: 'Silvassa Main Road',
  city: 'Silvassa',
  state: 'Dadra and Nagar Haveli',
  latitude: 20.2735,
  longitude: 73.0082,
  call_time: '26 Jun 2026 09:18',
  duration: '03:12',
  category: 'Road Accident',
  priority: 'Critical',
  severity_score: 92,
  status: 'Processing',
  emotion: 'Panic',
  emotion_score: 0.91,
  background_noise: 'Traffic',
  noise_level: 'Medium',
  vehicle_count: 3,
  injured_people: 4,
  fatalities: 0,
  ambulance_required: true,
  police_required: true,
  fire_required: false,
  incident_id: 'INC-001',
  transcript_raw:
    'Major accident on Silvassa Main Road near bus stand...',
  transcript_clean:
    'There has been a collision involving three vehicles. Four people are injured and require immediate medical assistance.',
  keywords: ['accident', 'injured', 'ambulance', 'traffic', 'bus stand'],
  audio_events: [
    { event: 'Car Crash', confidence: 98 },
    { event: 'People Screaming', confidence: 91 },
    { event: 'Vehicle Horn', confidence: 74 },
  ],
  score_breakdown: {
    category: 90,
    keywords: 100,
    emotion: 84,
    audio: 95,
    location: 90,
  },
  dispatches: [
    { department: 'Police', officer: 'Rajesh Kumar', status: 'Dispatched' },
    { department: 'Ambulance', officer: 'Unit 108-B', status: 'On Route' },
  ],
}

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const scoreRows = [
  { label: 'Category', value: MOCK_CALL_DETAILS.score_breakdown.category },
  { label: 'Keywords', value: MOCK_CALL_DETAILS.score_breakdown.keywords },
  { label: 'Emotion', value: MOCK_CALL_DETAILS.score_breakdown.emotion },
  { label: 'Audio', value: MOCK_CALL_DETAILS.score_breakdown.audio },
  { label: 'Location', value: MOCK_CALL_DETAILS.score_breakdown.location },
]

export default function CallViewerPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const call = { ...MOCK_CALL_DETAILS, id: id || MOCK_CALL_DETAILS.id }

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
                  <div className="font-medium">{call.address}, {call.city}, {call.state}</div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-zinc-500">Date</div>
                    <div className="font-medium">{call.call_time.split(' ')[0]} {call.call_time.split(' ')[1]} {call.call_time.split(' ')[2]}</div>
                  </div>
                  <div>
                    <div className="text-zinc-500">Time</div>
                    <div className="font-medium">{call.call_time.split(' ')[3]}</div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-zinc-500">Duration</div>
                    <div className="font-medium">{call.duration}</div>
                  </div>
                  <div>
                    <div className="text-zinc-500">Incident</div>
                    <button onClick={() => navigate(`/incidents/${call.incident_id}`)} className="text-sm text-blue-600 hover:underline">{call.incident_id}</button>
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
              <div><strong>Ambulance required:</strong> {call.ambulance_required ? 'Yes' : 'No'}</div>
              <div><strong>Police required:</strong> {call.police_required ? 'Yes' : 'No'}</div>
              <div><strong>Fire required:</strong> {call.fire_required ? 'Yes' : 'No'}</div>
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
                  {call.keywords.map((keyword) => (
                    <Badge key={keyword} className="bg-zinc-900 text-white">{keyword}</Badge>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-zinc-500">Emotion</div>
                  <div className="font-medium">{call.emotion}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Emotion Score</div>
                  <div className="font-medium">{(call.emotion_score * 100).toFixed(0)}%</div>
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
                    {call.audio_events.map((event) => (
                      <TableRow key={event.event}>
                        <TableCell>{event.event}</TableCell>
                        <TableCell>{event.confidence}%</TableCell>
                      </TableRow>
                    ))}
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
                <div className="text-5xl font-extrabold text-zinc-900">{call.severity_score}</div>
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
              {call.dispatches.map((dispatch) => (
                <div key={dispatch.department} className="rounded-lg border border-zinc-200 p-3">
                  <div className="font-medium">{dispatch.department}</div>
                  <div>{dispatch.officer}</div>
                  <div className="mt-1"><Badge className="bg-slate-800 text-white">{dispatch.status}</Badge></div>
                </div>
              ))}
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
            <div className="h-72 rounded-xl overflow-hidden border border-zinc-200">
              <MapContainer center={[call.latitude, call.longitude]} zoom={14} style={{ height: '100%', width: '100%' }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <Marker position={[call.latitude, call.longitude]}>
                  <Popup>
                    Caller Location<br />{call.address}
                  </Popup>
                </Marker>
              </MapContainer>
            </div>
            <div className="mt-3 text-sm text-zinc-500">Caller Location • {call.address}, {call.city}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Action Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm text-zinc-600">Use these actions to manage the investigation workflow. All buttons are placeholder actions for the current demo.</div>
            <div className="grid gap-2">
              <Button onClick={() => window.open(`tel:${call.caller_phone.replace(/\s/g, '')}`)}>Call Back</Button>
              <Button variant="outline" onClick={handleDownloadReport}>Download Report</Button>
              <Button variant="outline" onClick={() => window.print()}>Print Report</Button>
              <Button variant="outline" onClick={() => {}} >Play Audio</Button>
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
