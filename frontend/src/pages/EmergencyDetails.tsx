// @ts-nocheck
import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
// import { useQuery } from '@tanstack/react-query'
// import { getEmergency } from '@/api/emergencyApi'
import Card from '@/components/common/Card'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'

export default function EmergencyDetails() {
  const { id } = useParams()
  const navigate = useNavigate()

  // TODO: Replace with real API when backend ready
  const MOCK_CALL = {
    id: 'CALL-001',
    caller_name: 'Ramesh Patel',
    caller_phone: '+91 98765 43210',
    call_start_time: '26 Jun 2026, 09:12:34',
    duration: '3m 24s',
    language: 'English',
    status: 'Processing',
    category: 'Road Accident',
    latitude: 20.2766,
    longitude: 73.0144,
    location_text: 'Silvassa Main Road, near Bus Stand',
    priority_level: 'Critical',
    priority_color: 'text-red-600',
    final_score: 92.4,
    raw_transcript: 'Help! Major accident on Silvassa Main Road near the bus stand. A truck has hit two bikes. Three people are unconscious and there is heavy bleeding. Please send ambulance immediately. People are lying on the road.',
    cleaned_transcript: 'Major accident on Silvassa Main Road near bus stand. Truck hit two bikes. Three people unconscious, heavy bleeding. Ambulance needed immediately.',
    keywords: ['unconscious', 'heavy bleeding', 'truck', 'accident', 'bus stand'],
    classification: 'Road Accident',
    confidence: 0.94,
    model_used: 'MiniLM + Random Forest',
    audio_events: [
      { event_name: 'Screaming', confidence: 0.87, start_time: 0.5, end_time: 3.2 },
      { event_name: 'Vehicle Crash', confidence: 0.72, start_time: 8.1, end_time: 10.4 },
    ],
    score_breakdown: {
      category_score: 70.0, category_weight: '30%', category_contribution: 21.0,
      keyword_score: 100.0, keyword_weight: '25%', keyword_contribution: 25.0,
      emotion_score: 80.0, emotion_weight: '20%', emotion_contribution: 16.0,
      audio_score: 75.0, audio_weight: '15%', audio_contribution: 11.25,
      location_score: 65.0, location_weight: '10%', location_contribution: 6.5,
      matched_keywords: ['unconscious', 'heavy bleeding', 'truck'],
      total: 79.75,
    },
    pipeline_status: 'Scored',
    incident_id: 'INC-001',
    incident_title: 'Multi-vehicle collision Silvassa Main Road',
  }

  const call = MOCK_CALL
  const isLoading = false
  const error = null

  const scoreRows = [
    { component: 'Category', score: call.score_breakdown.category_score, weight: call.score_breakdown.category_weight, contribution: call.score_breakdown.category_contribution },
    { component: 'Keywords', score: call.score_breakdown.keyword_score, weight: call.score_breakdown.keyword_weight, contribution: call.score_breakdown.keyword_contribution },
    { component: 'Emotion', score: call.score_breakdown.emotion_score, weight: call.score_breakdown.emotion_weight, contribution: call.score_breakdown.emotion_contribution },
    { component: 'Audio', score: call.score_breakdown.audio_score, weight: call.score_breakdown.audio_weight, contribution: call.score_breakdown.audio_contribution },
    { component: 'Location', score: call.score_breakdown.location_score, weight: call.score_breakdown.location_weight, contribution: call.score_breakdown.location_contribution },
  ]

  const pipelineSteps = [
    { label: 'Received', state: 'completed' },
    { label: 'Uploaded', state: 'completed' },
    { label: 'Transcribed', state: 'completed' },
    { label: 'Classified', state: 'completed' },
    { label: 'Scored', state: 'completed' },
    { label: 'Correlated', state: 'pending' },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Emergency #{call.id}</h1>
      <div className="mb-4">
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-zinc-200 bg-white p-3 text-xs text-zinc-500">
          {pipelineSteps.map((step, idx) => (
            <div key={step.label} className="flex items-center gap-2">
              <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full ${step.state === 'completed' ? 'bg-emerald-100 text-emerald-600' : step.state === 'pending' ? 'bg-zinc-100 text-zinc-300' : 'bg-amber-100 text-amber-500'}`}>
                {step.state === 'completed' ? '✓' : step.state === 'pending' ? '○' : '⏳'}
              </span>
              <span>{step.label}</span>
              {idx < pipelineSteps.length - 1 && <span className="inline-block h-px w-8 bg-zinc-200" />}
            </div>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card title="Caller Information">
          <div className="space-y-2">
            <div className="text-lg font-semibold">{call.caller_name}</div>
            <div><strong>Phone:</strong> {call.caller_phone}</div>
            <div><strong>Time:</strong> {call.call_start_time}</div>
            <div><strong>Duration:</strong> {call.duration}</div>
            <div className="flex flex-wrap gap-2">
              <span className="inline-flex rounded-full bg-zinc-900 px-2 py-0.5 text-xs text-white">{call.language}</span>
              <span className="inline-flex rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-700">{call.status}</span>
            </div>
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div>
              <div className="text-sm font-medium mb-2">Raw Transcript</div>
              <div className="bg-zinc-50 p-3 rounded text-sm font-mono leading-relaxed">{call.raw_transcript}</div>
            </div>
            <div>
              <div className="text-sm font-medium mb-2">Cleaned Transcript</div>
              <div className="bg-white border p-3 rounded text-sm leading-relaxed">{call.cleaned_transcript}</div>
            </div>
          </div>

          <div className="mt-4">
            <div className="text-sm font-medium">Detected Keywords:</div>
            <div className="mt-2 flex flex-wrap gap-1">
              {call.keywords.map((keyword) => (
                <span key={keyword} className="bg-zinc-900 text-white text-xs px-2 py-0.5 rounded">{keyword}</span>
              ))}
            </div>
          </div>
        </Card>

        <Card title="Priority & AI Analysis">
          <div className="space-y-4">
            <div>
              <div className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${call.priority_color} bg-zinc-100`}>{call.priority_level}</div>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-500">Priority Score</div>
              <div className="text-2xl font-bold">{call.final_score} / 100</div>
            </div>

            <div>
              <div className="text-sm font-medium mb-2">Score Breakdown</div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm border border-zinc-200">
                  <thead>
                    <tr className="bg-zinc-50 text-left text-xs uppercase text-zinc-500">
                      <th className="px-3 py-2 border-r border-zinc-200">Component</th>
                      <th className="px-3 py-2 border-r border-zinc-200">Score</th>
                      <th className="px-3 py-2 border-r border-zinc-200">Weight</th>
                      <th className="px-3 py-2">Contribution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scoreRows.map((row) => (
                      <tr key={row.component} className="border-t border-zinc-200">
                        <td className="px-3 py-2">{row.component}</td>
                        <td className="px-3 py-2">{row.score.toFixed(1)}</td>
                        <td className="px-3 py-2">× {row.weight}</td>
                        <td className="px-3 py-2">= {row.contribution.toFixed(2)} pts</td>
                      </tr>
                    ))}
                    <tr className="border-t-2 border-zinc-300 font-bold">
                      <td className="px-3 py-2">TOTAL</td>
                      <td className="px-3 py-2">&nbsp;</td>
                      <td className="px-3 py-2">&nbsp;</td>
                      <td className="px-3 py-2">= {call.score_breakdown.total.toFixed(2)} pts</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-medium">Classification</div>
              <div>Category: <span className="font-medium">{call.classification}</span></div>
              <div className="text-sm">Confidence: {(call.confidence * 100).toFixed(0)}%</div>
              <div className="w-full h-2 rounded-full bg-zinc-200 overflow-hidden mt-1">
                <div className="h-full bg-zinc-900" style={{ width: `${call.confidence * 100}%` }} />
              </div>
              <div className="text-xs text-zinc-500">Model: {call.model_used}</div>
            </div>

            {call.audio_events?.length > 0 && (
              <div>
                <div className="text-sm font-medium mb-2">Audio Events</div>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm border border-zinc-200">
                    <thead>
                      <tr className="bg-zinc-50 text-left text-xs uppercase text-zinc-500">
                        <th className="px-3 py-2 border-r border-zinc-200">Event</th>
                        <th className="px-3 py-2 border-r border-zinc-200">Confidence</th>
                        <th className="px-3 py-2 border-r border-zinc-200">Start</th>
                        <th className="px-3 py-2">End</th>
                      </tr>
                    </thead>
                    <tbody>
                      {call.audio_events.map((event, index) => (
                        <tr key={index} className="border-t border-zinc-200">
                          <td className="px-3 py-2">{event.event_name}</td>
                          <td className="px-3 py-2">
                            <div className="text-xs text-zinc-600 mb-1">{(event.confidence * 100).toFixed(0)}%</div>
                            <div className="w-24 h-2 bg-zinc-200 rounded-full overflow-hidden">
                              <div className="h-full bg-emerald-600" style={{ width: `${event.confidence * 100}%` }} />
                            </div>
                          </td>
                          <td className="px-3 py-2">{event.start_time}s</td>
                          <td className="px-3 py-2">{event.end_time}s</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </Card>

        <Card title="Location Map">
          <div className="h-48">
            {call.latitude != null && call.longitude != null ? (
              <MapContainer center={[call.latitude, call.longitude]} zoom={14} style={{ height: '100%' }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <Marker position={[call.latitude, call.longitude]}>
                  <Popup>{call.location_text}</Popup>
                </Marker>
              </MapContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-gray-500">No location data available</div>
            )}
          </div>
          <div className="mt-3 text-sm text-zinc-500">{call.location_text}</div>
          <div className="mt-4 rounded-lg border border-zinc-200 bg-zinc-50 p-3">
            <div className="text-sm text-zinc-500">Linked Incident:</div>
            <div className="font-medium">{call.incident_title}</div>
            <button onClick={() => navigate(`/incidents/${call.incident_id}`)} className="mt-2 text-xs text-zinc-900 underline">View Incident →</button>
          </div>
        </Card>
      </div>

      <div className="mt-6">
        <Card title="Transcript">
          <pre className="whitespace-pre-wrap">{data.transcript}</pre>
        </Card>
      </div>
    </div>
  )
}
