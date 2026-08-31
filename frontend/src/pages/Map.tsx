// @ts-nocheck
import React from 'react'
import { MapContainer, TileLayer } from 'react-leaflet'

export default function MapPage() {
	return (
		<div className="max-w-6xl mx-auto">
			<h1 className="text-2xl font-bold mb-4">Map</h1>
			<div className="h-96 rounded overflow-hidden">
				<MapContainer center={[20.5937, 78.9629]} zoom={5} style={{height: '100%'}}>
					<TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
				</MapContainer>
			</div>
		</div>
	)
}
