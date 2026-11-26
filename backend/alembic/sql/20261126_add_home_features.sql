-- Migration: Add service_category to sos_alerts and new tables for Home features

ALTER TABLE sos_alerts
    ADD COLUMN IF NOT EXISTS service_category VARCHAR(30) DEFAULT 'general',
    ADD COLUMN IF NOT EXISTS category_source VARCHAR(30) DEFAULT 'user_selected';

CREATE INDEX IF NOT EXISTS ix_sos_alerts_service_category ON sos_alerts (service_category);

CREATE TABLE IF NOT EXISTS emergency_contacts (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    relation VARCHAR(50) NOT NULL,
    notify_on_sos BOOLEAN NOT NULL DEFAULT TRUE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_emergency_contacts_user_id ON emergency_contacts (user_id);

CREATE TABLE IF NOT EXISTS user_notifications (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    alert_id UUID REFERENCES sos_alerts(id) ON DELETE SET NULL,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_user_notifications_user_id ON user_notifications (user_id);
CREATE INDEX IF NOT EXISTS ix_user_notifications_alert_id ON user_notifications (alert_id);
CREATE INDEX IF NOT EXISTS ix_user_notifications_is_read ON user_notifications (is_read);
CREATE INDEX IF NOT EXISTS ix_user_notifications_created_at ON user_notifications (created_at);

CREATE TABLE IF NOT EXISTS track_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    share_token VARCHAR(128) NOT NULL UNIQUE,
    duration_hours INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_track_sessions_user_id ON track_sessions (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_track_sessions_share_token ON track_sessions (share_token);
CREATE INDEX IF NOT EXISTS ix_track_sessions_status ON track_sessions (status);
CREATE INDEX IF NOT EXISTS ix_track_sessions_expires_at ON track_sessions (expires_at);

CREATE TABLE IF NOT EXISTS track_points (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES track_sessions(id) ON DELETE CASCADE,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    accuracy_m DOUBLE PRECISION,
    battery_pct INTEGER,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_track_points_session_id ON track_points (session_id);
CREATE INDEX IF NOT EXISTS ix_track_points_recorded_at ON track_points (recorded_at);
