-- Migration: Add TrackMe share_with_control_room, sos_alert_id, and client_point_id

ALTER TABLE track_sessions
    ADD COLUMN IF NOT EXISTS share_with_control_room BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS sos_alert_id UUID REFERENCES sos_alerts(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_track_sessions_sos_alert_id ON track_sessions (sos_alert_id);

ALTER TABLE track_points
    ADD COLUMN IF NOT EXISTS client_point_id VARCHAR(64);

ALTER TABLE track_points
    ADD CONSTRAINT uq_track_point_client_id UNIQUE (session_id, client_point_id);
