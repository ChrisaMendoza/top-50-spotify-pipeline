SELECT
    track_id,
    TRIM(track_name) AS track_name,
    TRIM(artist_name) AS artist_name,
    country,
    popularity::INT AS popularity,
    ROUND(duration_ms / 1000.0 / 60, 2) AS duration_min,
    fetch_date
FROM staging.raw_tracks
WHERE track_id IS NOT NULL
