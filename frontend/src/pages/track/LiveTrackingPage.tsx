// @ts-nocheck
import React, { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Navigation, Clock, AlertTriangle, CheckCircle2, Activity, User } from 'lucide-react'

import { listOperatorTrackSessions, getOperatorTrackDetail } from '@/api/sosApi'
import { tokenStore } from '@/api/axiosClient'
import { API_BASE_URL, MAP_TILE_ATTRIBUTION, MAP_TILE_URL } from '@/lib/constants'
import { formatIST } from '@/lib/formatters'

const liveMarkerIcon = L.divIcon({
  html: `<div style="background-color:#7c3aed;width:18px;height:18px;border-radius:50%;border:3px solid #ffffff;box-shadow:0 0 10px #7c3aed;"></div>`,
  className: '',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

export default function LiveTrackingPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { data: listData, isLoading } = useQuery({
    queryKey: ['operator-track-list'],
    queryFn: listOperatorTrackSessions,
    refetchInterval: 4000,
  })

  const sessions = listData?.items || []

  useEffect(() => {
    if (!selectedId && sessions.length > 0) {
      setSelectedId(sessions[0].id)
    }
  }, [sessions, selectedId])

  const { data: detail } = useQuery({
    queryKey: ['operator-track-detail', selectedId],
    queryFn: () => getOperatorTrackDetail(selectedId!),
    enabled: !!selectedId,
    refetchInterval: 3000,
  })

  // Real-time WebSocket updates (<2s)
  useEffect(() => {
    const token = tokenStore.accessToken
    if (!token) return
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws') + `/track/ws/operator?token=${encodeURIComponent(token)}`
    let ws: WebSocket | null = null
    try {
      ws = new WebSocket(wsUrl)
      ws.onmessage = () => {
        queryClient.invalidateQueries({ queryKey: ['operator-track-list'] })
        if (selectedId) {
          queryClient.invalidateQueries({ queryKey: ['operator-track-detail', selectedId] })
        }
      }
    } catch {}
    return () => {
      try { ws?.close() } catch {}
    }
  }, [selectedId, queryClient])

  const points = detail?.points || []
  const lastPt = points.length > 0 ? points[points.length - 1] : null
  const pathCoords = points.map((p: any) => [p.latitude, p.longitude])
  const lastUpdatedMs = lastPt?.recorded_at ? new Date(lastPt.recorded_at).getTime() : 0
  const isStale = detail?.status === 'active' && lastUpdatedMs > 0 && Date.now() - lastUpdatedMs > 120000
  const isEnded = detail && (detail.status === 'ended' || detail.status === 'expired')

  const distMeters = detail?.distance_meters || 0
  const distDisplay = distMeters >= 1000 ? `${(distMeters / 1000).toFixed(2)} km` : `${Math.round(distMeters)} m`

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 flex items-center gap-2">
            <Navigation className="w-6 h-6 text-purple-600" /> Live Tracking (TrackMe)
          </h1>
          <p className="text-xs text-zinc-500">
            Real-time citizen sessions shared with the control room or linked to an active SOS alert.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Session List */}
        <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b bg-zinc-50 font-semibold text-sm">
            Shared &amp; SOS-Linked Sessions ({sessions.length})
          </div>
          {isLoading ? (
            <div className="p-6 text-center text-sm text-zinc-500">Loading sessions...</div>
          ) : sessions.length === 0 ? (
            <div className="p-6 text-center text-sm text-zinc-500">
              No active or shared TrackMe sessions.
            </div>
          ) : (
            <div className="divide-y max-h-[540px] overflow-y-auto">
              {sessions.map((s: any) => (
                <div
                  key={s.id}
                  onClick={() => setSelectedId(s.id)}
                  className={`p-4 cursor-pointer hover:bg-zinc-50 transition-colors ${
                    selectedId === s.id ? 'bg-purple-50 border-l-4 border-purple-600' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm text-zinc-900">{s.user_name}</span>
                    <span
                      className={`text-[11px] font-bold uppercase px-2 py-0.5 rounded-full ${
                        s.status === 'active'
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-zinc-200 text-zinc-700'
                      }`}
                    >
                      {s.status}
                    </span>
                  </div>
                  <div className="text-xs text-zinc-500 mt-1">
                    {s.sos_alert_id ? 'Linked to Active SOS' : 'Shared with Control Room'} • {s.duration_hours}h
                  </div>
                  <div className="text-[11px] text-zinc-400 mt-0.5">{formatIST(s.started_at)}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Live Map Panel */}
        <div className="lg:col-span-2 bg-white border rounded-xl overflow-hidden shadow-sm flex flex-col">
          {!detail ? (
            <div className="p-12 text-center text-zinc-500 text-sm">
              Select a TrackMe session to inspect live coordinates and path.
            </div>
          ) : (
            <>
              <div className="px-4 py-3 border-b flex flex-wrap items-center justify-between gap-3 bg-zinc-50">
                <div className="flex items-center gap-4 text-xs">
                  <span className="inline-flex items-center gap-1 font-semibold text-zinc-800">
                    <Clock className="w-3.5 h-3.5 text-purple-600" />
                    Last update: {lastPt ? formatIST(lastPt.recorded_at) : 'Waiting for GPS'}
                  </span>
                  <span className="inline-flex items-center gap-1 font-semibold text-zinc-800">
                    <Activity className="w-3.5 h-3.5 text-blue-600" />
                    Distance: {distDisplay}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => navigate(`/users/${detail.user_id}`)}
                    className="text-xs text-blue-600 hover:underline inline-flex items-center gap-1 font-medium"
                  >
                    <User className="w-3.5 h-3.5" /> Citizen Profile
                  </button>
                  {detail.sos_alert_id && (
                    <button
                      onClick={() => navigate(`/sos/${detail.sos_alert_id}`)}
                      className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded font-semibold"
                    >
                      Open Linked SOS
                    </button>
                  )}
                </div>
              </div>

              {isStale && (
                <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-xs text-amber-800 flex items-center gap-2 font-medium">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  No update for 2+ minutes — GPS signal or network may be lost.
                </div>
              )}

              {isEnded && (
                <div className="bg-zinc-100 border-b px-4 py-2 text-xs text-zinc-700 flex items-center gap-2 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-zinc-500" />
                  Session {detail.status}. Showing last recorded track path.
                </div>
              )}

              <div className="h-[460px] w-full">
                {lastPt ? (
                  <MapContainer
                    key={`${detail.id}-${lastPt.latitude}-${lastPt.longitude}`}
                    center={[lastPt.latitude, lastPt.longitude]}
                    zoom={16}
                    style={{ width: '100%', height: '100%' }}
                  >
                    <TileLayer url={MAP_TILE_URL} attribution={MAP_TILE_ATTRIBUTION} />
                    {pathCoords.length > 1 && (
                      <Polyline positions={pathCoords} pathOptions={{ color: '#7c3aed', weight: 4 }} />
                    )}
                    <Marker position={[lastPt.latitude, lastPt.longitude]} icon={liveMarkerIcon}>
                      <Popup>
                        Last Update: {formatIST(lastPt.recorded_at)}
                        <br />
                        Accuracy: {lastPt.accuracy_m ? `±${Math.round(lastPt.accuracy_m)}m` : 'N/A'}
                      </Popup>
                    </Marker>
                    {lastPt.accuracy_m && (
                      <Circle
                        center={[lastPt.latitude, lastPt.longitude]}
                        radius={lastPt.accuracy_m}
                        pathOptions={{ color: '#7c3aed', fillColor: '#7c3aed', fillOpacity: 0.15 }}
                      />
                    )}
                  </MapContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-zinc-500">
                    No GPS coordinates recorded yet.
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
