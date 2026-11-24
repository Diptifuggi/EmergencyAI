# EmergencyIQ geospatial infrastructure

This directory documents the intentionally separate geospatial stack. It must not use the EmergencyIQ application database.

## Current state

- FastAPI reads `NOMINATIM_URL` and defaults to `http://localhost:8080`.
- React reads `VITE_MAP_TILE_URL` and `VITE_MAP_TILE_ATTRIBUTION`; its development default is the standard OpenStreetMap raster tile endpoint.
- Flutter reads `MAP_TILE_URL` from `--dart-define` and defaults to a local Android-emulator tile endpoint.
- No India PBF has been downloaded or imported automatically.

## Safe deployment gate

The development laptop has about 7.77 GB RAM, PostgreSQL 18, no PostGIS detected in `emergencyiq_db`, no Docker, and no WSL2. Do not run an India-wide Nominatim import on this laptop without first provisioning a separate host/database and checking memory, disk, PostGIS, and `osm2pgsql`.

Use WSL2 or Docker only after manual installation and review. Keep the Nominatim PostgreSQL database separate from `emergencyiq_db`; never point `DATABASE_URL` at it.

The official India extract is available from Geofabrik:
<https://download.geofabrik.de/asia/india.html>

Official Nominatim installation guidance:
<https://nominatim.org/release-docs/develop/admin/Installation/>

For a first proof of concept, use a smaller India regional extract on a separate host. The full India extract is approximately 1.6 GB before import/index/database overhead and is not equivalent to total disk or RAM requirements.

## Runtime contract

For production, configure a geocoding service and tile provider approved for the application's traffic. Public Nominatim requests are cached, serialized, and limited to at most one request per second per backend process; configure an identifying `NOMINATIM_USER_AGENT` with an operator contact before using the public service. The in-memory cache is process-local, so use a self-hosted service or shared cache for multi-worker/high-volume deployments.

The React development default uses `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`; the public tile service requires a working browser network connection, normal interactive use, and visible attribution. Do not bulk-download or prefetch its tiles. If the configured tile provider is unreachable, the UI reports that state and continues to show coordinates and the independent saved snapshot.

Provide the tile provider's required attribution in the map UI. For OpenStreetMap tiles use `© OpenStreetMap contributors`.
