"""
producer.py
Lit les tracks du jour depuis PostgreSQL et les publie
dans le topic Kafka spotify-tracks, un par un.
Tourne à l'intérieur du container Airflow donc utilise kafka:9092.
"""

import psycopg2
import json
import time
from kafka import KafkaProducer
from datetime import date

TOPIC = "spotify-tracks"


def get_db_connection():
    return psycopg2.connect(
        host="postgres",
        dbname="spotify_db",
        user="spotify",
        password="spotify123",
    )


def get_todays_tracks(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT track_id, track_name, artist_name, country, popularity
        FROM staging.raw_tracks
        WHERE fetch_date = %s
        """,
        (date.today(),),
    )
    rows = cursor.fetchall()
    cursor.close()
    return [
        {"track_id": r[0], "track_name": r[1], "artist_name": r[2],
         "country": r[3], "popularity": r[4]}
        for r in rows
    ]


def run():
    producer = KafkaProducer(
        bootstrap_servers="kafka:9092",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    conn = get_db_connection()
    tracks = get_todays_tracks(conn)
    conn.close()

    print(f"{len(tracks)} tracks à publier dans Kafka...")
    for track in tracks:
        producer.send(TOPIC, value=track)
        print(f"Publié : {track['track_name']} ({track['country']})")
        time.sleep(0.5)

    producer.flush()
    print("Tous les tracks ont été publiés.")


if __name__ == "__main__":
    run()
