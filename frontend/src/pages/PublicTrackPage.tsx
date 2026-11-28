// @ts-nocheck
import React, { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { MapPin, Clock, ShieldAlert, CheckCircle2, AlertTriangle } from 'lucide-react'

import { getPublicTrack } from '@/api/sosApi'
import { API_BASE_URL, MAP_TILE_ATTRIBUTION, MAP_TILE_URL } from '@/lib/constants'
import { formatIST } from '@/lib/formatters'

const trackMarkerIcon = L.divIcon({
  html: `<div style="background-color:#7c3aed;width:20px;height:20px;border-radius:50%;border:3px solid #ffffff;box-shadow:0 0 10px #7c3aed;"></div>`,
  className: '',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
})

export default function PublicTrackPage() {
  const { token } = useParams<{ token: string }>()
  const queryClient = useQueryClient()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['public-track', token],
    queryFn: () => getPublicTrack(token!),
    enabled: !!token,
    refetchInterval: 4000,
  })

  useEffect(() => {
    if (!token) return
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws') + `/public/track/ws/${encodeURIComponent(token)}`
    let ws: WebSocket | null = null
    try {
      ws = new WebSocket(wsUrl)
      ws.onmessage = () => {
        queryClient.invalidateQueries({ queryKey: ['public-track', token] })
      }
    } catch {}
    return () => {
      try { ws?.close() } catch {}
    }
  }, [token, queryClient])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#111] text-white flex items-center justify-center">
        Loading live location...
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="min-h-screen bg-[#111] text-white flex flex-col items-center justify-center p-6 text-center">
        <ShieldAlert className="w-12 h-12 text-red-500 mb-3" />
        <h1 className="text-xl font-bold">Tracking Session Unavailable</h1>
        <p className="text-sm text-zinc-400 mt-1">
          This TrackMe link is invalid or no longer available.
        </p>
      </div>
    )
  }

  const isEnded = data.status === 'ended' || data.status === 'expired'
  const pos = data.last_position
  const lastMs = pos?.recorded_at ? new Date(pos.recorded_at).getTime() : 0
  const isStale = !isEnded && lastMs > 0 && Date.now() - lastMs > 120000

  return (
    <div className="min-h-screen bg-[#111] text-white flex flex-col">
      <header className="bg-[#181818] border-b border-[#262626] px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <MapPin className="w-6 h-6 text-purple-400" />
          <div>
            <h1 className="text-lg font-bold">
              EmergencyIQ TrackMe {data.first_name ? `• ${data.first_name}` : ''}
            </h1>
            <p className="text-xs text-zinc-400 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              Last updated: {formatIST(data.updated_at)}
            </p>
          </div>
        </div>
        <div>
          {isEnded ? (
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-zinc-700 text-zinc-200">
              Session {data.status === 'expired' ? 'Expired' : 'Ended'}
            </span>
          ) : (
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-600/20 text-emerald-400 border border-emerald-500/40 inline-flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> Live Sharing Active
            </span>
          )}
        </div>
      </header>

      {isStale && (
        <div className="bg-amber-500/20 border-b border-amber-500/40 px-6 py-2 text-center text-xs text-amber-200 font-medium flex items-center justify-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          No update for 2+ minutes — awaiting GPS signal.
        </div>
      )}

      {isEnded && (
        <div className="bg-amber-500/15 border-b border-amber-500/30 px-6 py-2.5 text-center text-xs text-amber-300 font-medium">
          This location sharing session has ended. Showing the last recorded position.
        </div>
      )}

      <main className="flex-1 relative min-h-[450px]">
        {pos ? (
          <MapContainer
            center={[pos.latitude, pos.longitude]}
            zoom={16}
            style={{ width: '100%', height: '100%', minHeight: '500px' }}
          >
            <TileLayer url={MAP_TILE_URL} attribution={MAP_TILE_ATTRIBUTION} />
            <Marker position={[pos.latitude, pos.longitude]} icon={trackMarkerIcon}>
              <Popup>
                {data.first_name || 'User'}'s last position
                <br />
                Accuracy: {pos.accuracy_m ? `±${Math.round(pos.accuracy_m)}m` : 'N/A'}
              </Popup>
            </Marker>
            {pos.accuracy_m && (
              <Circle
                center={[pos.latitude, pos.longitude]}
                radius={pos.accuracy_m}
                pathOptions={{ color: '#7c3aed', fillColor: '#7c3aed', fillOpacity: 0.15 }}
              />
            )}
          </MapContainer>
        ) : (
          <div className="flex items-center justify-center h-96 text-zinc-400 text-sm">
            No GPS coordinates recorded for this session yet.
          </div>
        )}
      </main>
    </div>
  )
}
