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
SELECT *
FROM ranked
WHERE rank <= 10
ORDER BY fetch_date DESC, country, rank
