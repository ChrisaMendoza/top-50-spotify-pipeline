CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS staging.raw_tracks (
    id          SERIAL PRIMARY KEY,
    track_id    VARCHAR(100),
    track_name  VARCHAR(300),
    artist_name VARCHAR(300),
    album_name  VARCHAR(300),
    country     VARCHAR(10),
    popularity  INT,
    duration_ms INT,
    fetch_date  DATE DEFAULT CURRENT_DATE,
    fetched_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE (track_id, country, fetch_date)
);

CREATE TABLE IF NOT EXISTS analytics.live_feed (
    id          SERIAL PRIMARY KEY,
    track_id    VARCHAR(100),
    track_name  VARCHAR(300),
    artist_name VARCHAR(300),
    country     VARCHAR(10),
    popularity  INT,
    received_at TIMESTAMP DEFAULT NOW()
);
