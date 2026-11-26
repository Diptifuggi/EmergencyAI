// @ts-nocheck
import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import {
  Siren,
  Phone,
  ArrowLeft,
  MapPin,
  Clock,
  ShieldAlert,
  VolumeX,
  AlertTriangle,
  User,
  HeartPulse,
  Activity,
  CheckCircle2,
  XCircle,
  FileText,
} from 'lucide-react'

import {
  getSosDetail,
  acknowledgeSos,
  verifySos,
  closeSos,
  markFalseAlarmSos,
  SOSDetail,
} from '@/api/sosApi'
import { MAP_TILE_ATTRIBUTION, MAP_TILE_URL } from '@/lib/constants'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui'

function formatDateTime(dateStr?: string | Date): string {
  if (!dateStr) return '-'
  const d = typeof dateStr === 'string' ? new Date(dateStr) : dateStr
  if (isNaN(d.getTime())) return '-'
  return `${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })} • ${d.toLocaleDateString([], { day: '2-digit', month: 'short' })}`
}

// Custom Leaflet Pulse Marker for SOS
const sosMarkerIcon = L.divIcon({
  html: `<div style="background-color:#ef4444;width:24px;height:24px;border-radius:50%;border:3px solid #ffffff;box-shadow:0 0 12px #ef4444;" class="animate-ping"></div>`,
  className: '',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
})

export default function SosDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [actionNote, setActionNote] = useState<string>('')
  const [activeModal, setActiveModal] = useState<'ack' | 'verify' | 'close' | 'false_alarm' | null>(null)

  // 5s Polling for live coordinates & status
  const { data: alert, isLoading, error } = useQuery<SOSDetail>({
    queryKey: ['sos', 'detail', id],
    queryFn: () => getSosDetail(id!),
    enabled: !!id,
    refetchInterval: 5000,
  })

  // Action Mutations
  const ackMutation = useMutation({
    mutationFn: () => acknowledgeSos(id!, actionNote),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sos'] })
      setActiveModal(null)
      setActionNote('')
    },
  })

  const verifyMutation = useMutation({
    mutationFn: () => verifySos(id!, actionNote),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sos'] })
      setActiveModal(null)
      setActionNote('')
    },
  })

  const closeMutation = useMutation({
    mutationFn: () => closeSos(id!, actionNote),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sos'] })
      setActiveModal(null)
      setActionNote('')
    },
  })

  const falseAlarmMutation = useMutation({
    mutationFn: () => markFalseAlarmSos(id!, actionNote),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sos'] })
      setActiveModal(null)
      setActionNote('')
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px] text-zinc-400">
        <Activity className="w-6 h-6 animate-spin mr-2" />
        Loading SOS alert details and encrypted snapshot...
      </div>
    )
  }

  if (error || !alert) {
    return (
      <div className="p-8 text-center">
        <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-2" />
        <h2 className="text-xl font-bold text-white">Alert Not Found</h2>
        <p className="text-zinc-400 mt-1">The requested SOS alert does not exist or access was denied.</p>
        <button
          onClick={() => navigate('/sos')}
          className="mt-4 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 text-sm"
        >
          Back to SOS List
        </button>
      </div>
    )
  }

  const snapshot = alert.profile_snapshot || {}
  const hasCoordinates = alert.latitude != null && alert.longitude != null
  const locationUpdates = alert.location_updates || []
  const events = alert.events || []

  // Route path history for leaflet polyline
  const polylineCoords = locationUpdates
    .filter((u) => u.latitude != null && u.longitude != null)
    .map((u) => [u.latitude, u.longitude] as [number, number])

  const center: [number, number] = hasCoordinates
    ? [alert.latitude!, alert.longitude!]
    : [20.5937, 78.9629] // Fallback India center

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Action bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/sos')}
            className="p-2 bg-[#202020] hover:bg-[#282828] text-zinc-300 rounded-lg transition-colors border border-[#303030]"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-red-600/20 text-red-400 border border-red-500/30">
                {alert.alert_type.toUpperCase()}
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                STATUS: {alert.status.toUpperCase()}
              </span>
            </div>
            <h1 className="text-xl font-bold text-white mt-1">
              SOS Incident #{alert.id.substring(0, 8)}
            </h1>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {alert.status === 'pending' && (
            <button
              onClick={() => setActiveModal('ack')}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition-colors shadow"
            >
              Acknowledge
            </button>
          )}

          {(alert.status === 'pending' || alert.status === 'acknowledged') && (
            <button
              onClick={() => setActiveModal('verify')}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-colors shadow"
            >
              Verify Incident
            </button>
          )}

          {alert.status !== 'closed' && alert.status !== 'cancelled' && alert.status !== 'false_alarm' && (
            <>
              <button
                onClick={() => setActiveModal('false_alarm')}
                className="px-4 py-2 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-600/40 rounded-lg text-xs font-semibold transition-colors"
              >
                Mark False Alarm
              </button>
              <button
                onClick={() => setActiveModal('close')}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 rounded-lg text-xs font-semibold transition-colors"
              >
                Close SOS
              </button>
            </>
          )}
        </div>
      </div>

      {/* Flag Notice */}
      <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3">
        <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
        <div className="text-xs text-red-200">
          <span className="font-bold text-red-400">URGENT HUMAN VERIFICATION REQUIRED:</span> This alert bypassed AI
          analysis. Emergency type is classified as <strong>unknown_emergency / silent_sos</strong> until verified by an
          authorized operator.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Live GPS Map (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="bg-[#181818] border-[#262626] overflow-hidden shadow-lg">
            <CardHeader className="py-3 px-4 border-b border-[#262626] flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                <MapPin className="w-4 h-4 text-red-500" />
                Live Incident Coordinates & Location History
              </CardTitle>
              {hasCoordinates ? (
                <span className="text-xs text-emerald-400 font-mono">
                  {alert.latitude?.toFixed(5)}, {alert.longitude?.toFixed(5)} (±{Math.round(alert.accuracy_m || 0)}m)
                </span>
              ) : (
                <span className="text-xs text-amber-400 font-semibold">
                  Location Unavailable ({alert.location_status})
                </span>
              )}
            </CardHeader>
            <CardContent className="p-0 h-[400px] relative">
              {hasCoordinates ? (
                <MapContainer
                  center={center}
                  zoom={15}
                  scrollWheelZoom={false}
                  style={{ height: '100%', width: '100%' }}
                >
                  <TileLayer
                    attribution={MAP_TILE_ATTRIBUTION}
                    url={MAP_TILE_URL || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'}
                  />
                  <Marker position={center} icon={sosMarkerIcon}>
                    <Popup>
                      <div className="text-zinc-900 text-xs">
                        <strong>SOS Trigger Position</strong>
                        <br />
                        Lat: {alert.latitude?.toFixed(4)}, Lon: {alert.longitude?.toFixed(4)}
                        <br />
                        Status: {alert.location_status}
                      </div>
                    </Popup>
                  </Marker>
                  {alert.accuracy_m && (
                    <Circle
                      center={center}
                      radius={alert.accuracy_m}
                      pathOptions={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.15 }}
                    />
                  )}
                  {polylineCoords.length > 1 && (
                    <Polyline positions={polylineCoords} pathOptions={{ color: '#3b82f6', weight: 3 }} />
                  )}
                </MapContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center p-8 text-center bg-[#141414]">
                  <MapPin className="w-12 h-12 text-zinc-600 mb-2" />
                  <h4 className="text-base font-semibold text-zinc-300">Location Unavailable</h4>
                  <p className="text-xs text-zinc-500 max-w-sm mt-1">
                    Device coordinates were denied or unavailable at alert trigger time. Operators must contact the citizen directly via telephone.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Timeline Audit Events */}
          <Card className="bg-[#181818] border-[#262626]">
            <CardHeader className="py-3 px-4 border-b border-[#262626]">
              <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-400" />
                Audit Trail & Timeline
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              {events.length === 0 ? (
                <p className="text-xs text-zinc-500">No events logged yet.</p>
              ) : (
                <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#2b2b2b]">
                  {events.map((evt, idx) => (
                    <div key={evt.id || idx} className="relative">
                      <div className="absolute -left-6 top-1 w-3 h-3 rounded-full bg-blue-500 border-2 border-[#181818]" />
                      <div className="text-xs">
                        <span className="font-semibold text-white uppercase">{evt.event_type.replace('_', ' ')}</span>
                        <span className="text-zinc-500 ml-2">by {evt.actor_type}</span>
                        {evt.created_at && (
                          <span className="text-zinc-500 ml-2">
                            • {formatDateTime(evt.created_at)}
                          </span>
                        )}
                        {evt.payload && (
                          <pre className="mt-1 p-2 bg-[#121212] rounded text-[11px] text-zinc-400 font-mono overflow-x-auto">
                            {JSON.stringify(evt.payload, null, 2)}
                          </pre>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Citizen Profile Snapshot & Medical Details (1 Col) */}
        <div className="space-y-6">
          <Card className="bg-[#181818] border-[#262626] shadow-lg">
            <CardHeader className="py-3 px-4 border-b border-[#262626]">
              <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                <User className="w-4 h-4 text-emerald-400" />
                Decrypted Citizen Profile Snapshot
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4 text-xs">
              <div>
                <span className="text-zinc-500">Full Name:</span>
                <p className="text-sm font-bold text-white mt-0.5">
                  {snapshot.full_name || snapshot.username || 'Anonymous User'}
                </p>
              </div>

              {snapshot.phone ? (
                <div>
                  <span className="text-zinc-500">Primary Phone:</span>
                  <div className="mt-1">
                    <a
                      href={`tel:${snapshot.phone}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600/20 text-emerald-400 border border-emerald-600/40 rounded-lg font-bold hover:bg-emerald-600/30 text-xs"
                    >
                      <Phone className="w-3.5 h-3.5" />
                      Call {snapshot.phone}
                    </a>
                  </div>
                </div>
              ) : (
                <div>
                  <span className="text-zinc-500">Primary Phone:</span>
                  <p className="text-zinc-400 italic">Not registered</p>
                </div>
              )}

              {snapshot.alternate_phone && (
                <div>
                  <span className="text-zinc-500">Alternate Phone:</span>
                  <p className="text-zinc-200 mt-0.5 font-mono">{snapshot.alternate_phone}</p>
                </div>
              )}

              {snapshot.guardian_phone && (
                <div>
                  <span className="text-zinc-500">
                    Guardian Phone ({snapshot.guardian_relation || 'Parent/Child'}):
                  </span>
                  <div className="mt-1">
                    <a
                      href={`tel:${snapshot.guardian_phone}`}
                      className="inline-flex items-center gap-1 text-blue-400 hover:underline font-mono"
                    >
                      <Phone className="w-3 h-3" />
                      {snapshot.guardian_phone}
                    </a>
                  </div>
                </div>
              )}

              {snapshot.address && (
                <div>
                  <span className="text-zinc-500">Registered Address:</span>
                  <p className="text-zinc-300 mt-0.5">{snapshot.address}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#262626]">
                <div>
                  <span className="text-zinc-500">Age:</span>
                  <p className="text-zinc-200 font-semibold">{snapshot.age ? `${snapshot.age} yrs` : 'N/A'}</p>
                </div>
                <div>
                  <span className="text-zinc-500">Blood Group:</span>
                  <p className="text-red-400 font-bold">{snapshot.blood_group || 'Unknown'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Medical Details Card */}
          <Card className="bg-[#181818] border-[#262626] shadow-lg">
            <CardHeader className="py-3 px-4 border-b border-[#262626]">
              <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                <HeartPulse className="w-4 h-4 text-red-400" />
                Medical Information & Allergies
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4 text-xs">
              <div>
                <span className="text-zinc-500">Medical Consent:</span>
                <p className="mt-0.5">
                  {snapshot.medical_consent ? (
                    <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Consent Granted at Registration
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-amber-400 font-medium">
                      <XCircle className="w-3.5 h-3.5" /> No Medical Consent on Record
                    </span>
                  )}
                </p>
              </div>

              <div>
                <span className="text-zinc-500">Allergies:</span>
                <div className="mt-1 p-2 bg-[#202020] rounded text-zinc-200 font-mono">
                  {snapshot.allergies || 'None declared'}
                </div>
              </div>

              <div>
                <span className="text-zinc-500">Medical History:</span>
                <div className="mt-1 p-2 bg-[#202020] rounded text-zinc-200 font-mono">
                  {snapshot.medical_history || 'None declared'}
                </div>
              </div>

              <div className="pt-2 border-t border-[#262626] text-[11px] text-zinc-500">
                Audit Note: Accessing this drawer logs operator credentials to the secure audit access table.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Action Dialog Modal */}
      {activeModal && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-[#1c1c1c] border border-zinc-700 rounded-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-white capitalize">
              {activeModal.replace('_', ' ')} Incident
            </h3>
            <p className="text-xs text-zinc-400">
              Provide an optional operational note or dispatch reference for the audit trail.
            </p>
            <textarea
              value={actionNote}
              onChange={(e) => setActionNote(e.target.value)}
              placeholder="e.g. Dispatched ambulance team #4 / Verified via callback"
              className="w-full bg-[#141414] border border-zinc-700 rounded-lg p-3 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-red-500"
              rows={3}
            />
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => {
                  setActiveModal(null)
                  setActionNote('')
                }}
                className="px-4 py-2 bg-zinc-800 text-zinc-300 rounded-lg text-xs font-semibold hover:bg-zinc-700"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (activeModal === 'ack') ackMutation.mutate()
                  if (activeModal === 'verify') verifyMutation.mutate()
                  if (activeModal === 'close') closeMutation.mutate()
                  if (activeModal === 'false_alarm') falseAlarmMutation.mutate()
                }}
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-bold hover:bg-red-500"
              >
                Confirm Action
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
