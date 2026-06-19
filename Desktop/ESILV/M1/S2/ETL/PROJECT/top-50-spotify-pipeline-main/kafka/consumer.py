"""
consumer.py
Écoute le topic Kafka spotify-tracks et insère chaque message
dans analytics.live_feed.
Ce script tourne sur ton Mac donc utilise localhost:29092
(le port exposé par Docker pour Kafka).
"""

import psycopg2
import json
from kafka import KafkaConsumer

TOPIC = "spotify-tracks"


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        dbname="spotify_db",
        user="spotify",
        password="spotify123",
    )


def insert_live_track(conn, track):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO analytics.live_feed (track_id, track_name, artist_name, country, popularity)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (track["track_id"], track["track_name"], track["artist_name"],
         track["country"], track["popularity"]),
    )
    conn.commit()
    cursor.close()


def run():
    # localhost:29092 car ce script tourne sur le Mac, pas dans Docker
    # c'est le port Kafka exposé dans docker-compose
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers="localhost:29092",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        # "earliest" = lit depuis le début du topic si ce consumer n'a jamais tourné
        auto_offset_reset="earliest",
        # group_id permet à Kafka de mémoriser où on en est dans la lecture
        group_id="spotify-consumer-group",
    )

    conn = get_db_connection()
    print("Consumer démarré, en attente de messages...")

    # boucle infinie : le consumer reste ouvert et traite chaque message dès qu'il arrive
    for message in consumer:
        track = message.value
        insert_live_track(conn, track)
        print(f"Reçu : {track['track_name']} ({track['country']})")


if __name__ == "__main__":
    run()
