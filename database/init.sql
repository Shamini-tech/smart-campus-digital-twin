CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS readings (
    time                TIMESTAMPTZ NOT NULL,
    reading_id          TEXT NOT NULL,
    building_id         TEXT NOT NULL,
    floor_id            TEXT NOT NULL,
    device_id           TEXT NOT NULL,
    device_type         TEXT NOT NULL,
    metric              TEXT NOT NULL,
    value               DOUBLE PRECISION,
    unit                TEXT NOT NULL,
    source_type         TEXT NOT NULL,
    data_quality_status TEXT NOT NULL,
    fault_label         TEXT NOT NULL DEFAULT 'none',
    received_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (reading_id, time)
);

SELECT create_hypertable('readings', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS readings_device_time ON readings (device_id, time DESC);