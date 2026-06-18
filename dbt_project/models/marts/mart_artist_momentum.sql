WITH today AS (
    SELECT artist_name, country, ROUND(AVG(popularity), 1) AS pop_today
    FROM {{ ref('stg_tracks') }}
    WHERE fetch_date = CURRENT_DATE
    GROUP BY artist_name, country
),
yesterday AS (
    SELECT artist_name, country, ROUND(AVG(popularity), 1) AS pop_yesterday
    FROM {{ ref('stg_tracks') }}
    WHERE fetch_date = CURRENT_DATE - INTERVAL '1 day'
    GROUP BY artist_name, country
)
SELECT
    t.country,
    t.artist_name,
    t.pop_today,
    y.pop_yesterday,
    ROUND(t.pop_today - COALESCE(y.pop_yesterday, t.pop_today), 1) AS momentum_score
FROM today t
LEFT JOIN yesterday y ON t.artist_name = y.artist_name AND t.country = y.country
ORDER BY momentum_score DESC
