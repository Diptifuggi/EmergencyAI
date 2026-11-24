import React, { useEffect, useState } from 'react'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import axiosClient from '@/api/axiosClient'
import { API_BASE_URL, MAP_TILE_ATTRIBUTION, MAP_TILE_URL } from '@/lib/constants'

import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

function MapViewport({ latitude, longitude }: { latitude: number; longitude: number }) {
  const map = useMap()

  useEffect(() => {
    const container = map.getContainer()
    const observer = new ResizeObserver(() => map.invalidateSize())
    observer.observe(container)
    map.invalidateSize()
    return () => observer.disconnect()
  }, [map])

  useEffect(() => {
    map.setView([latitude, longitude], 14)
  }, [latitude, longitude, map])

  return null
}

function StoredMapSnapshot({
  available,
  url,
}: {
  available: boolean
  url: string | null
}) {
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null)
  const [failure, setFailure] = useState<string | null>(null)

  useEffect(() => {
    if (!available || !url || typeof window === 'undefined') {
      setSnapshotUrl(null)
      setFailure(null)
      return
    }

    let active = true
    let objectUrl: string | null = null
    setSnapshotUrl(null)
    setFailure(null)
    let resolvedUrl: URL
    try {
      const baseValue = API_BASE_URL.endsWith('/') ? API_BASE_URL : `${API_BASE_URL}/`
      const backendBase = new URL(baseValue, window.location.origin)
      resolvedUrl = new URL(url, backendBase)
      if (resolvedUrl.origin !== backendBase.origin) {
        const configuredPath = backendBase.pathname.replace(/\/$/, '')
        if (!configuredPath || !resolvedUrl.pathname.startsWith(`${configuredPath}/`)) {
          throw new Error('Snapshot URL is outside the configured backend origin.')
        }
        resolvedUrl = new URL(
          `${resolvedUrl.pathname}${resolvedUrl.search}${resolvedUrl.hash}`,
          backendBase.origin,
        )
      }
    } catch {
      setFailure('The snapshot URL is invalid or outside the configured backend.')
      return () => {
        active = false
      }
    }

    axiosClient.get(resolvedUrl.toString(), { responseType: 'blob' })
      .then(({ data, headers }) => {
        if (!active) return
        const contentType = String(headers['content-type'] || data.type || '').split(';')[0]
        if (!(data instanceof Blob) || data.size === 0 || !contentType.startsWith('image/')) {
          console.warn('Stored map snapshot response was not a non-empty image.')
          setFailure('The snapshot endpoint returned an empty or non-image response.')
          return
        }
        objectUrl = URL.createObjectURL(data)
        setSnapshotUrl(objectUrl)
      })
      .catch((error) => {
        if (!active) return
        const statusCode = error?.response?.status
        console.warn('Stored map snapshot request failed.', { status: statusCode ?? null })
        setFailure(statusCode === 404
          ? 'The saved snapshot file is missing.'
          : statusCode
            ? `The snapshot request failed with HTTP ${statusCode}.`
            : 'The snapshot could not be reached. Check the backend connection.')
      })

    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [available, url])

  if (!available && url) return <p className="mt-3 text-sm text-amber-800">A saved snapshot reference exists, but the image file is unavailable.</p>
  if (!available) return <p className="mt-3 text-sm text-zinc-500">No stored map snapshot is available.</p>
  if (failure) return <p className="mt-3 text-sm text-amber-800">{failure}</p>
  if (!url) return <p className="mt-3 text-sm text-amber-800">A snapshot is marked available, but its URL was not provided.</p>
  if (!snapshotUrl) return <p className="mt-3 text-sm text-zinc-500">Loading stored map snapshot…</p>

  return (
    <figure className="mt-4">
      <figcaption className="mb-2 text-sm font-medium text-zinc-700">Stored map snapshot</figcaption>
      <img
        src={snapshotUrl}
        alt="Map snapshot saved with this emergency call"
        onError={() => {
          console.warn('Stored map snapshot could not be decoded as an image.')
          URL.revokeObjectURL(snapshotUrl)
          setSnapshotUrl(null)
          setFailure('The saved snapshot is not a valid or readable image.')
        }}
        className="max-h-80 w-full rounded border border-zinc-200 object-contain"
      />
    </figure>
  )
}

export default function CallerLocationMap({
  latitude,
  longitude,
  accuracy,
  address,
  addressStatus = 'unavailable',
  status,
  capturedAt = null,
  coordinateStatus = 'missing',
  coordinatesConflict = false,
  snapshotAvailable = false,
  snapshotUrl = null,
  label = 'Caller GPS location',
}: {
  latitude: number | null
  longitude: number | null
  accuracy: number | null
  address: string | null
  addressStatus?: string | null
  status: string | null
  capturedAt?: string | null
  coordinateStatus?: 'valid' | 'invalid' | 'missing'
  coordinatesConflict?: boolean
  snapshotAvailable?: boolean
  snapshotUrl?: string | null
  label?: string
}) {
  const [tilesFailed, setTilesFailed] = useState(false)
  const [tilesLoading, setTilesLoading] = useState(true)
  const hasCoordinates = latitude !== null && longitude !== null

  useEffect(() => {
    setTilesFailed(false)
    setTilesLoading(true)
  }, [latitude, longitude])

  const formattedCaptureTime = capturedAt && !Number.isNaN(Date.parse(capturedAt))
    ? new Date(capturedAt).toLocaleString()
    : null

  return (
    <div>
      {hasCoordinates ? (
        <div className="relative h-72 overflow-hidden rounded-xl border border-zinc-200">
          <MapContainer
            center={[latitude, longitude]}
            zoom={14}
            style={{ height: '100%', width: '100%' }}
            scrollWheelZoom={false}
          >
            <MapViewport latitude={latitude} longitude={longitude} />
            <TileLayer
              url={MAP_TILE_URL}
              attribution={MAP_TILE_ATTRIBUTION}
              maxZoom={19}
              eventHandlers={{
                loading: () => {
                  setTilesFailed(false)
                  setTilesLoading(true)
                },
                load: () => setTilesLoading(false),
                tileerror: () => {
                  setTilesLoading(false)
                  setTilesFailed(true)
                },
              }}
            />
            <Marker position={[latitude, longitude]}>
              <Popup>{label}</Popup>
            </Marker>
          </MapContainer>
          {tilesFailed && (
            <div className="absolute inset-x-0 bottom-0 z-[1000] bg-white/95 p-3 text-sm text-amber-900 shadow">
              Live map tiles are unavailable. Coordinates and any saved snapshot remain available below.
            </div>
          )}
          {!tilesFailed && tilesLoading && (
            <div className="absolute inset-x-0 bottom-0 z-[1000] bg-white/95 p-3 text-sm text-zinc-700 shadow">
              Loading live map tiles…
            </div>
          )}
        </div>
      ) : (
        <div className="flex h-72 items-center justify-center rounded-xl border border-zinc-200 bg-zinc-50 text-sm text-zinc-500">
          {coordinateStatus === 'invalid'
            ? 'The saved GPS coordinates are invalid.'
            : 'No GPS coordinates were provided.'}
        </div>
      )}
      <div className="mt-3 space-y-1 text-sm text-zinc-600">
        <div><span className="font-medium">{label} (not independently verified as the incident location):</span> {hasCoordinates ? `${latitude.toFixed(6)}, ${longitude.toFixed(6)}` : 'Not available'}</div>
        <div><span className="font-medium">Address for these coordinates:</span> {address || (addressStatus === 'pending' ? 'Resolving address…' : 'Address unavailable')}</div>
        <div><span className="font-medium">Incident location verification:</span> Not independently verified</div>
        <div><span className="font-medium">Address lookup:</span> {
          addressStatus === 'pending'
            ? 'Pending'
            : addressStatus === 'resolved'
              ? 'Resolved from coordinates'
              : addressStatus === 'reported'
                ? 'Caller-reported; not geocoded'
                : addressStatus === 'unknown'
                  ? 'Stored address; source not recorded'
                  : addressStatus === 'failed'
                    ? 'Failed; address unavailable'
                    : 'Unavailable'
        }</div>
        <div><span className="font-medium">Accuracy:</span> {accuracy === null ? 'Not available' : `${accuracy.toFixed(1)} m`}</div>
        <div><span className="font-medium">Location status:</span> {status || 'Not reported'}</div>
        <div><span className="font-medium">Captured:</span> {formattedCaptureTime || 'Not available'}</div>
        {coordinatesConflict && (
          <div className="text-amber-800">
            Coordinate fields differed; the saved top-level coordinates are shown.
          </div>
        )}
      </div>
      <StoredMapSnapshot available={snapshotAvailable} url={snapshotUrl} />
    </div>
  )
}
