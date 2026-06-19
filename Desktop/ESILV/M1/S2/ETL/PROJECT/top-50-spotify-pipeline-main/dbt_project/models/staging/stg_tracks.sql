-- modèle de staging : on nettoie les données brutes avant de les passer aux marts
SELECT
    track_id,
    TRIM(track_name) AS track_name,       -- enlève les espaces en trop dans les noms
    TRIM(artist_name) AS artist_name,
    country,
    popularity::INT AS popularity,
    ROUND(duration_ms / 1000.0 / 60, 2) AS duration_min,  -- on convertit ms en minutes
    fetch_date
FROM staging.raw_tracks
WHERE track_id IS NOT NULL  -- filtre les lignes corrompues sans identifiant
