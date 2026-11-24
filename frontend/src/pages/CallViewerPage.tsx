// @ts-nocheck
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
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
import { normalizeEmergencyCall } from '@/lib/emergencyCallNormalizer'
import CallerLocationMap from '@/components/CallerLocationMap'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'

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

  const normalizedCall = normalizeEmergencyCall(emergency)
  const analysis = normalizedCall.analysis
  const metadata = emergency.client_metadata || {}
  const helpRequired = normalizedCall.helpRequired
  const recommendation = normalizedCall.dispatchRecommendation
  const recommendedUnits = normalizedCall.recommendedUnits
  const emergencyNumbers = recommendation.emergency_numbers && typeof recommendation.emergency_numbers === 'object'
    ? recommendation.emergency_numbers
    : {}
  const latitude = normalizedCall.latitude
  const longitude = normalizedCall.longitude
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
  const keywords = normalizedCall.emergencyKeywords
  const audioEvents = Array.isArray((emergency as any)?.audio_events) ? (emergency as any).audio_events : []
  const dispatches = normalizedCall.dispatchRecords
  const helpHas = (terms: string[]) => helpRequired.some((item: string) =>
    terms.includes(String(item).trim().toLowerCase())
  )
  const serviceState = (terms: string[]) => {
    if (helpHas(terms)) return 'Recommended'
    return Array.isArray(analysis.help_required) ? 'Not recommended' : 'Not reported'
  }
  const indicatorState = (key: string) => {
    if (analysis[key] === true) return 'Detected'
    if (analysis[key] === false) return 'Not detected'
    return 'Not reported'
  }
  const transcript = normalizedCall.cleanTranscript
  const rawTranscript = normalizedCall.textContent || normalizedCall.transcription || 'Not available'
  const call = {
    id: emergency.id,
    caller_name: normalizedCall.callerName || 'Not provided',
    caller_phone: normalizedCall.callerPhone || 'Not provided',
    caller_email: normalizedCall.callerEmail || 'Not provided',
    age: metadata.age ?? 'Not available',
    gender: typeof metadata.gender === 'string' && metadata.gender.trim() ? metadata.gender : 'Not available',
    language: normalizedCall.language || 'Not reported',
    source: normalizedCall.source || normalizedCall.platform || 'Not reported',
    call_type: emergency.call_type || 'Not available',
    status: emergency.status || 'Not available',
    priority: normalizedCall.priority || 'Not reported',
    category: normalizedCall.category
      ? normalizedCall.category.replaceAll('_', ' ').replace(/\b\w/g, (letter: string) => letter.toUpperCase())
      : 'Not reported',
    sub_type: normalizedCall.subType || 'Not reported',
    address: normalizedCall.locationAddress || 'Address not available',
    city,
    state,
    latitude,
    longitude,
    call_date: callDate,
    call_clock: callClock,
    updated_at: updatedAt && !Number.isNaN(updatedAt.getTime()) ? updatedAt.toLocaleString('en-GB') : 'Not available',
    duration: 'Not available',
    severity: analysis.severity ?? 'Not reported',
    priority_score: normalizedCall.priorityScore,
    confidence: normalizedCall.confidence,
    incident_description: analysis.incident_description || 'Not reported',
    caller_request: analysis.caller_request || 'Not reported',
    victim_count: typeof analysis.victim_count === 'number' ? analysis.victim_count : null,
    ambulance_recommended: serviceState(['ambulance', 'medical_assistance']),
    police_recommended: analysis.police_required === true || helpHas(['police']) ? 'Recommended' : indicatorState('police_required'),
    fire_recommended: serviceState(['fire_service']),
    rescue_recommended: serviceState(['rescue']),
    injuries: indicatorState('injuries_present'),
    fatalities: 'Not reported',
    incident_id: null,
    transcript_raw: rawTranscript,
    transcript_clean: transcript || 'Not reported separately',
    keywords,
    audio_events: audioEvents,
    audio_url: emergency.audio_url || null,
    map_snapshot_url: normalizedCall.mapSnapshotUrl,
    score_breakdown: {
      category: normalizedCall.category || 'Not reported',
      keywords: keywords.length ? keywords.join(', ') : 'Not available',
      emotion: typeof analysis.panic_score === 'number' ? analysis.panic_score : 'Not measured',
      audio: emergency.audio_file_size != null ? `${emergency.audio_file_size} bytes` : 'Not available',
      location: latitude !== null && longitude !== null ? `${latitude.toFixed(5)}, ${longitude.toFixed(5)}` : 'Not available',
    },
    dispatches,
    emergency_numbers: emergencyNumbers,
    help_required: helpRequired,
    recommended_units: recommendedUnits,
    recommendation,
    human_confirmation_required: analysis.human_confirmation_required,
    location_accuracy: normalizedCall.locationAccuracy,
    location_status: normalizedCall.locationStatus,
    map_snapshot_available: normalizedCall.mapSnapshotAvailable,
  }
  const scoreRows = [
    { label: 'Category', value: call.score_breakdown.category ?? 'Not available' },
    { label: 'Keywords', value: call.score_breakdown.keywords ?? 'Not available' },
    { label: 'Emotion', value: call.score_breakdown.emotion ?? 'Not available' },
    { label: 'Audio', value: call.score_breakdown.audio ?? 'Not available' },
    { label: 'Location', value: call.score_breakdown.location ?? 'Not available' },
  ]
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
                  <div className="font-medium">{call.address}</div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><div className="text-zinc-500">City</div><div className="font-medium">{call.city}</div></div>
                  <div><div className="text-zinc-500">State</div><div className="font-medium">{call.state}</div></div>
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
              <div><strong>People reported:</strong> {call.victim_count == null ? 'Not reported' : call.victim_count}</div>
              <div><strong>Injuries:</strong> {call.injuries}</div>
              <div><strong>Fatalities:</strong> {call.fatalities}</div>
              <div><strong>Ambulance:</strong> {call.ambulance_recommended}</div>
              <div><strong>Police:</strong> {call.police_recommended}</div>
              <div><strong>Fire service:</strong> {call.fire_recommended}</div>
              <div><strong>Rescue:</strong> {call.rescue_recommended}</div>
              <div><strong>Other reported hazards:</strong> {[
                ['Smoke', analysis.smoke_present],
                ['Fire', analysis.fire_present],
                ['Explosion', analysis.explosion_present],
                ['Entrapment', analysis.trapped_persons],
                ['Weapon', analysis.weapon_present],
                ['Flood risk', analysis.flood_risk],
                ['LPG leak', analysis.lpg_leak],
              ].filter(([, value]) => value === true).map(([label]) => label).join(', ') || 'None detected'}</div>
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
                <div><div className="text-zinc-500">Emergency type</div><div className="font-medium">{call.category}</div></div>
                <div><div className="text-zinc-500">Subtype</div><div className="font-medium">{call.sub_type}</div></div>
                <div><div className="text-zinc-500">Severity</div><div className="font-medium">{call.severity}</div></div>
                <div><div className="text-zinc-500">Priority</div><div className="font-medium">{call.priority}</div></div>
                <div><div className="text-zinc-500">Priority score</div><div className="font-medium">{call.priority_score ?? 'Not reported'}</div></div>
                <div><div className="text-zinc-500">Confidence</div><div className="font-medium">{call.confidence == null ? 'Not available' : `${(call.confidence * 100).toFixed(0)}%`}</div></div>
                <div><div className="text-zinc-500">Victim count</div><div className="font-medium">{call.victim_count ?? 'Not reported'}</div></div>
              </div>
              <div>
                <div className="text-sm text-zinc-500">Incident description</div>
                <div className="mt-2 text-sm leading-6">{call.incident_description}</div>
              </div>
              <div>
                <div className="text-sm text-zinc-500">Caller request</div>
                <div className="mt-2 text-sm leading-6">{call.caller_request}</div>
              </div>
              <div className="grid gap-3 text-sm sm:grid-cols-2">
                <div><div className="text-zinc-500">Recommended help</div><div>{call.help_required.length ? call.help_required.join(', ') : 'Not reported'}</div></div>
                <div><div className="text-zinc-500">Recommended response units</div><div>{call.recommended_units.length ? call.recommended_units.join(', ') : 'None mapped'}</div></div>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-zinc-500">Panic estimate</div>
                  <div className="font-medium">{analysis.panic_level || 'Not measured'}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Panic score</div>
                  <div className="font-medium">{typeof analysis.panic_score === 'number' ? analysis.panic_score : 'Not measured'}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Background Noise</div>
                  <div className="font-medium">Not analyzed</div>
                </div>
                <div>
                  <div className="text-zinc-500">Noise Level</div>
                  <div className="font-medium">Not analyzed</div>
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
              <CardTitle>Analysis Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-center">
                <div className="text-5xl font-extrabold text-zinc-900">{call.priority_score ?? 'Not available'}</div>
                <div className="text-sm text-zinc-500">Operational priority score / 100</div>
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                <Badge className="bg-indigo-600 text-white">Severity: {call.severity}</Badge>
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
              {call.human_confirmation_required === true ? (
                <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-amber-900">
                  AI recommendations only. Human dispatcher confirmation is required before any dispatch.
                </div>
              ) : (
                <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-zinc-700">
                  AI-generated recommendation; operational confirmation status is not available.
                </div>
              )}
              <div><strong>Recommendation reason:</strong> {call.recommendation.reason || 'Not reported'}</div>
              <div><strong>Priority reason:</strong> {call.recommendation.priority_reason || 'Not reported'}</div>
              <div><strong>Dispatcher action:</strong> {call.recommendation.dispatcher_action || 'Not reported'}</div>
              <div>
                <strong>Configured emergency numbers:</strong>
                {Object.keys(call.emergency_numbers).length
                  ? <ul className="mt-1 list-inside list-disc">{Object.entries(call.emergency_numbers).map(([number, label]) => <li key={number}>{number}: {String(label)}</li>)}</ul>
                  : <span> Not reported</span>}
              </div>
              {Array.isArray(call.dispatches) && call.dispatches.length > 0 ? call.dispatches.map((dispatch, index) => (
                <div key={dispatch.id || dispatch.department || index} className="rounded-lg border border-zinc-200 p-3">
                  <div className="font-medium">{dispatch.department || dispatch.details?.department || dispatch.details?.unit || dispatch.details?.service || 'Recorded dispatch'}</div>
                  {dispatch.officer && <div>{dispatch.officer}</div>}
                  <div className="mt-1"><Badge className="bg-slate-800 text-white">{dispatch.status || 'Recorded'}</Badge></div>
                </div>
              )) : <div className="text-sm text-zinc-500">No confirmed operational dispatch is recorded for this call.</div>}
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
            <CallerLocationMap
              latitude={latitude}
              longitude={longitude}
              accuracy={normalizedCall.locationAccuracy}
              address={normalizedCall.locationAddress}
              addressStatus={normalizedCall.locationAddressStatus}
              status={normalizedCall.locationStatus}
              capturedAt={normalizedCall.locationTimestamp}
              coordinateStatus={normalizedCall.locationCoordinatesStatus}
              coordinatesConflict={normalizedCall.locationCoordinatesConflict}
              snapshotAvailable={normalizedCall.mapSnapshotAvailable}
              snapshotUrl={normalizedCall.mapSnapshotUrl}
              label="Caller device GPS location"
            />
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
