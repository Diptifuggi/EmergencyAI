# EmergencyIQ geospatial infrastructure

This directory documents the intentionally separate geospatial stack. It must not use the EmergencyIQ application database.

## Current state

- FastAPI reads `NOMINATIM_URL` and defaults to `http://localhost:8080`.
- Flutter reads `MAP_TILE_URL` from `--dart-define` and defaults to a local Android-emulator tile endpoint.
- No public Nominatim or public OSM tile URL is used by the application.
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

Start a self-hosted Nominatim service at `NOMINATIM_URL`, and a separate self-hosted tile service at `MAP_TILE_URL`. Reverse geocoding is enrichment: if Nominatim is unavailable, EmergencyIQ still stores raw GPS and completes analysis. Map tile failure affects visualization only.

Provide OpenStreetMap attribution in any deployed map UI: `© OpenStreetMap contributors`.
