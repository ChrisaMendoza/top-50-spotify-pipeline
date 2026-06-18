-- ROW_NUMBER() avec PARTITION BY crée un rang indépendant par pays et par jour
-- rang 1 = track le plus populaire dans ce pays ce jour-là
WITH ranked AS (
    SELECT
        fetch_date,
        country,
        track_name,
        artist_name,
        popularity,
        ROW_NUMBER() OVER (PARTITION BY country, fetch_date ORDER BY popularity DESC) AS rank
    FROM {{ ref('stg_tracks') }}
)
-- on garde seulement le top 10 pour chaque pays
SELECT *
FROM ranked
WHERE rank <= 10
ORDER BY fetch_date DESC, country, rank
