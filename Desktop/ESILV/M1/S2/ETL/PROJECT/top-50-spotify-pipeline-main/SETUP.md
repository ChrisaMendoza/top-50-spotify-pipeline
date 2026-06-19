# SETUP — Lancer le projet en local

Tout tourne dans Docker, sauf le consumer Kafka que je lance à la main dans un
terminal (comme ça on voit les messages arriver en direct pendant la démo).

Testé sur Mac (Apple Silicon, M1). Compte ~5 min au premier démarrage, le temps
qu'Airflow installe ses dépendances.

---

## Prérequis

- Docker Desktop installé et lancé
- Python 3.11 en local (juste pour le consumer Kafka)
- Un compte développeur Spotify (gratuit) pour les clés API

---

## 1. Les clés Spotify

Va sur [developer.spotify.com](https://developer.spotify.com) → *Dashboard* → *Create app*.
Récupère le **Client ID** et le **Client Secret**.

Dans le dashboard de l'app, mets n'importe quel Redirect URI valide
(`http://127.0.0.1:8080`) — on ne s'en sert pas, on est en flux **Client
Credentials**, mais Spotify oblige à en renseigner un.

Crée un fichier `.env` à la racine du projet :

```env
SPOTIFY_CLIENT_ID=ton_client_id
SPOTIFY_CLIENT_SECRET=ton_client_secret
```

> Le `.env` est dans le `.gitignore`, donc tes clés ne partent pas sur GitHub.

---

## 2. Démarrer la stack Docker

```bash
docker-compose up -d
```

Ça lance 7 services :

| Conteneur | Rôle | Port |
|---|---|---|
| `spotify_postgres` | base de données (staging + analytics) | 5432 |
| `spotify_zookeeper` | coordination Kafka | — |
| `spotify_kafka` | broker de streaming | 9092 / 29092 |
| `spotify_airflow_init` | crée la base Airflow + l'user admin, puis s'arrête | — |
| `spotify_airflow_scheduler` | exécute les tâches du DAG | — |
| `spotify_airflow` | interface web d'Airflow | 8080 |
| `spotify_dashboard` | dashboard Streamlit | 8501 |

`spotify_airflow_init` est normal s'il apparaît en `Exited` : il ne sert qu'au
premier setup.

---

## 3. Vérifier que tout est prêt

```bash
docker ps
```

Tu dois voir 6 conteneurs en `Up` (init exclu).

Vérifie qu'Airflow a fini de démarrer :

```bash
docker logs spotify_airflow --tail 5
```

Quand tu vois `Listening at: http://0.0.0.0:8080`, c'est bon.

---

## 4. Lancer le pipeline depuis Airflow

- Va sur <http://localhost:8080>
- Login : `admin` / `admin`
- Active le DAG `spotify_pipeline` (le toggle à gauche)
- Clique sur ▶️ pour le déclencher tout de suite (sinon il part tout seul à
  l'heure pile, schedule `@hourly`)

Le DAG fait, dans l'ordre : `fetch_spotify_data` → `run_dbt_models` →
`publish_to_kafka`. Les 3 tâches doivent passer au vert.

---

## 5. Lancer le consumer Kafka (dans un autre terminal)

Le consumer tourne en local et lit le topic Kafka exposé par Docker sur le port
29092 :

```bash
pip install -r requirements.txt
python kafka/consumer.py
```

Tu vas voir les tracks s'afficher au fur et à mesure qu'ils sont consommés et
insérés dans `analytics.live_feed`. Laisse ce terminal ouvert pendant la démo.

---

## 6. Ouvrir le dashboard

<http://localhost:8501>

Le bloc "Flux Live" en bas se remplit avec les messages reçus depuis Kafka.
Bouton *Rafraîchir* + toggle *auto-refresh 10s* pour le voir bouger en direct.

---

## Tout arrêter

```bash
docker-compose down          # arrête les conteneurs
docker-compose down -v       # + supprime le volume Postgres (repart de zéro)
```

---

## Petits pièges rencontrés (Mac M1)

- **Docker Desktop doit être lancé** avant `docker-compose up`, sinon erreur de
  connexion au démon.
- Si un port est déjà pris (5432, 8080, 8501), c'est souvent un vieux conteneur
  ou un Postgres local qui traîne : `docker ps -a` puis `docker rm -f <id>`.
- Le **momentum** et la **courbe d'évolution** dans le dashboard ont besoin
  d'au moins 2 jours de collecte pour afficher quelque chose — c'est normal
  qu'ils soient vides au premier lancement.
- Si Airflow met du temps : c'est le `pip install` des dépendances au premier
  démarrage, c'est ponctuel.
