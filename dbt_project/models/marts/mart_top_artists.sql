SELECT
    fetch_date,
    country,
    artist_name,
    COUNT(DISTINCT track_id)   AS nb_tracks_in_top50,
    ROUND(AVG(popularity), 1)  AS avg_popularity
FROM {{ ref('stg_tracks') }}
GROUP BY fetch_date, country, artist_name
ORDER BY fetch_date DESC, avg_popularity DESC
