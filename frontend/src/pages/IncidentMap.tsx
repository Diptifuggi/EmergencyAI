// @ts-nocheck
import React from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import { useQuery } from '@tanstack/react-query'
import { getEmergencies } from '@/api/emergencyApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'

export default function IncidentMap() {
  const { data, isLoading, error } = useQuery({ queryKey: ['emergencies-map'], queryFn: () => getEmergencies() })

  if (isLoading) return <Loading />
  if (error) return <ErrorMessage error={error} />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Incident Map</h1>
      <div className="h-[600px]">
        <MapContainer center={[20.5937,78.9629]} zoom={5} style={{height:'100%'}}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {data?.filter(call => call?.location && call.location.lat != null && call.location.lng != null).map(call => (
            <Marker key={call.id} position={[call.location.lat, call.location.lng]}>
              <Popup>
                <div className="font-semibold">{call.category} ({call.priority})</div>
                <div>{call.caller}</div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}
