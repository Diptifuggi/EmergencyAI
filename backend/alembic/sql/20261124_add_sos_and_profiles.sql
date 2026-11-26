-- SQL Migration for EmergencyIQ SOS and User Profile feature
-- Applied on PostgreSQL database: emergencyiq_db

-- 1. user_profiles
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    phone VARCHAR(20),
    alternate_phone VARCHAR(20),
    guardian_phone VARCHAR(20),
    guardian_relation VARCHAR(50),
    address TEXT,
    age INTEGER,
    blood_group VARCHAR(20) DEFAULT 'unknown',
    allergies TEXT,
    medical_history TEXT,
    medical_consent BOOLEAN NOT NULL DEFAULT FALSE,
    medical_consent_at TIMESTAMP WITH TIME ZONE,
    profile_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_profiles_user_id ON user_profiles(user_id);

-- 2. sos_alerts
CREATE TABLE IF NOT EXISTS sos_alerts (
    id UUID PRIMARY KEY,
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    alert_type VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    accuracy_m DOUBLE PRECISION,
    location_status VARCHAR(30) NOT NULL DEFAULT 'unavailable',
    triggered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    battery_pct INTEGER,
    network_type VARCHAR(50),
    device_id VARCHAR(128),
    app_version VARCHAR(50),
    profile_snapshot_encrypted TEXT,
    acknowledged_by UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    verified_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancel_reason TEXT,
    close_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sos_alerts_status ON sos_alerts(status);
CREATE INDEX IF NOT EXISTS ix_sos_alerts_received_at ON sos_alerts(received_at);
CREATE INDEX IF NOT EXISTS ix_sos_alerts_user_id ON sos_alerts(user_id);
CREATE INDEX IF NOT EXISTS ix_sos_alerts_alert_type ON sos_alerts(alert_type);
CREATE INDEX IF NOT EXISTS ix_sos_alerts_idempotency_key ON sos_alerts(idempotency_key);

-- 3. sos_location_updates
CREATE TABLE IF NOT EXISTS sos_location_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES sos_alerts(id) ON DELETE CASCADE,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    accuracy_m DOUBLE PRECISION,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sos_location_updates_alert_id ON sos_location_updates(alert_id);

-- 4. sos_events
CREATE TABLE IF NOT EXISTS sos_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES sos_alerts(id) ON DELETE CASCADE,
    actor_type VARCHAR(20) NOT NULL,
    actor_id UUID,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sos_events_alert_id ON sos_events(alert_id);

-- 5. sos_profile_access_log
CREATE TABLE IF NOT EXISTS sos_profile_access_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES sos_alerts(id) ON DELETE CASCADE,
    operator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    accessed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sos_profile_access_log_alert_id ON sos_profile_access_log(alert_id);
CREATE INDEX IF NOT EXISTS ix_sos_profile_access_log_operator_id ON sos_profile_access_log(operator_id);
