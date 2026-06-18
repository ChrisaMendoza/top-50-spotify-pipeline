import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Spotify Trends", page_icon="🎵", layout="wide")

st.markdown("""
<style>
body, .main, .block-container { background-color: #121212 !important; color: #FFFFFF; }
h1, h2, h3, h4 { color: #1DB954 !important; }
.stMetric { background-color: #1a1a1a; border-radius: 8px; padding: 12px; border: 1px solid #282828; }
div[data-testid="stMetricValue"] { color: #1DB954 !important; font-size: 2em !important; font-weight: bold !important; }
div[data-testid="stMetricLabel"] { color: #b3b3b3 !important; font-size: 0.85em !important; }
.stSelectbox label { color: #b3b3b3 !important; }
.section-title { font-size: 1.1em; font-weight: bold; color: #FFFFFF; margin-bottom: 4px; }
.section-sub { font-size: 0.78em; color: #b3b3b3; margin-bottom: 12px; font-style: italic; }
hr { border-color: #282828 !important; }
</style>
""", unsafe_allow_html=True)

PLOTLY_THEME = dict(
    paper_bgcolor="#1a1a1a", plot_bgcolor="#1a1a1a",
    font=dict(color="#FFFFFF", family="Arial"),
    margin=dict(l=10, r=10, t=30, b=10),
)

# Liste des pays suivis dans notre pipeline
COUNTRIES = ["FR", "US", "JP", "BR", "GB"]

@st.cache_resource
def get_conn():
    return psycopg2.connect(host="postgres", dbname="spotify_db", user="spotify", password="spotify123")

def load(query, params=None):
    try:
        return pd.read_sql(query, get_conn(), params=params)
    except:
        return pd.DataFrame()

# ── Header ─────────────────────────────────────────────────────────────────────

col_logo, col_title, col_kpi1, col_kpi2, col_kpi3, col_select = st.columns([0.5, 1.5, 1.5, 1.5, 1.5, 1.5])

with col_logo:
    st.markdown("<div style='background:#1DB954;border-radius:50%;width:48px;height:48px;display:flex;align-items:center;justify-content:center;font-size:24px;margin-top:8px'>🎵</div>", unsafe_allow_html=True)

with col_title:
    st.markdown("<h2 style='margin:0;padding:0;color:#1DB954 !important'>Spotify Trends</h2>", unsafe_allow_html=True)
    st.markdown("<span style='color:#b3b3b3;font-size:0.8em'>Mise à jour toutes les heures via Airflow</span>", unsafe_allow_html=True)

# KPIs globaux : pas de filtre pays ici, on veut toujours les totaux du jour
df_kpi = load("SELECT COUNT(DISTINCT track_name) AS tracks, COUNT(DISTINCT artist_name) AS artists, COUNT(DISTINCT country) AS countries FROM staging.raw_tracks WHERE fetch_date = CURRENT_DATE")
tracks    = int(df_kpi['tracks'].iloc[0])    if not df_kpi.empty else 0
artists   = int(df_kpi['artists'].iloc[0])   if not df_kpi.empty else 0
countries = int(df_kpi['countries'].iloc[0]) if not df_kpi.empty else 0

with col_kpi1:
    st.metric("Total Tracks", f"{tracks:,}")
with col_kpi2:
    st.metric("Total Artists", f"{artists:,}")
with col_kpi3:
    st.metric("Countries", f"{countries}")
with col_select:
    # "Global" = tous les pays confondus, sinon on filtre sur un seul pays
    country = st.selectbox("Pays analysé", ["Global", "FR", "US", "JP", "BR", "GB"])

st.markdown("<hr>", unsafe_allow_html=True)

# ── Ligne 1 : Top Artistes | Top Tracks ────────────────────────────────────────

c1, c2 = st.columns(2)

with c1:
    st.markdown('<p class="section-title">🎤 Top 5 Artistes</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Artistes avec la popularité moyenne la plus haute aujourd\'hui</p>', unsafe_allow_html=True)

    if country == "Global":
        # Pas de filtre pays : on prend les meilleurs artistes sur tous les marchés
        df_artists = load("""
            SELECT artist_name,
                   ROUND(AVG(popularity), 1) AS avg_pop,
                   ROW_NUMBER() OVER (ORDER BY AVG(popularity) DESC) AS rank
            FROM staging.raw_tracks
            WHERE fetch_date = CURRENT_DATE
            GROUP BY artist_name
            ORDER BY avg_pop DESC
            LIMIT 5
        """)
    else:
        df_artists = load("""
            SELECT artist_name,
                   ROUND(AVG(popularity), 1) AS avg_pop,
                   ROW_NUMBER() OVER (ORDER BY AVG(popularity) DESC) AS rank
            FROM staging.raw_tracks
            WHERE country = %(c)s AND fetch_date = CURRENT_DATE
            GROUP BY artist_name
            ORDER BY avg_pop DESC
            LIMIT 5
        """, params={"c": country})

    if not df_artists.empty:
        df_artists["label"] = df_artists["rank"].astype(str) + ". " + df_artists["artist_name"].str[:22]
        fig = go.Figure(go.Bar(
            x=df_artists["avg_pop"], y=df_artists["label"],
            orientation="h",
            marker=dict(color="#1DB954", line=dict(width=0)),
            text=df_artists["avg_pop"].astype(str),
            textposition="outside", textfont=dict(color="#1DB954", size=12),
        ))
        fig.update_layout(**PLOTLY_THEME, height=280,
                          xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                          yaxis=dict(autorange="reversed", tickfont=dict(color="#FFFFFF", size=12)))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Lance le pipeline Airflow pour voir les données.")

with c2:
    st.markdown('<p class="section-title">🏆 Top 10 Tracks</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Tracks les mieux classés aujourd\'hui — modèle dbt mart_top_tracks</p>', unsafe_allow_html=True)

    if country == "Global":
        df_top = load("""
            WITH unique_tracks AS (
                SELECT track_name,
                       artist_name,
                       MAX(popularity) AS popularity
                FROM analytics.mart_top_tracks
                WHERE fetch_date = CURRENT_DATE
                GROUP BY track_name, artist_name
            )
            SELECT track_name,
                   artist_name,
                   popularity,
                   ROW_NUMBER() OVER (ORDER BY popularity DESC) AS rank
            FROM unique_tracks
            ORDER BY popularity DESC
            LIMIT 10
        """)
    else:
        df_top = load("""
            SELECT rank, track_name, artist_name, popularity
            FROM analytics.mart_top_tracks
            WHERE country = %(c)s AND fetch_date = CURRENT_DATE
            ORDER BY rank
            LIMIT 10
        """, params={"c": country})

    if not df_top.empty:
        # On crée un label "Position. Titre · Artiste" pour chaque barre
        df_top["label"] = df_top["rank"].astype(str) + ". " + df_top["track_name"].str[:20] + " · " + df_top["artist_name"].str[:16]
        n = len(df_top)
        greens = [f"#{max(0, 29 - i*2):02x}{max(100, 185 - i*8):02x}{max(30, 84 - i*5):02x}" for i in range(n)]
        fig2 = go.Figure(go.Bar(
            x=df_top["popularity"], y=df_top["label"],
            orientation="h",
            marker=dict(color=greens, line=dict(width=0)),
            text=df_top["popularity"].astype(str),
            textposition="outside", textfont=dict(color="#FFFFFF", size=11),
            hovertext=df_top["artist_name"],
        ))
        fig2.update_layout(**PLOTLY_THEME, height=280,
                           xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                           yaxis=dict(autorange="reversed", tickfont=dict(color="#FFFFFF", size=11)))
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

st.markdown("<hr>", unsafe_allow_html=True)

# ── Ligne 2 : Carte | Momentum Artistes ────────────────────────────────────────

c3, c4 = st.columns(2)

with c3:
    st.markdown('<p class="section-title">🌍 Popularité par Pays</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Score de popularité moyen par marché surveillé</p>', unsafe_allow_html=True)

    # La carte montre toujours les 5 pays, pas besoin de filtrer
    df_map = load("SELECT country, ROUND(AVG(popularity), 1) AS avg_pop FROM staging.raw_tracks WHERE fetch_date = CURRENT_DATE GROUP BY country")
    COUNTRY_NAMES = {"FR": "France", "US": "United States", "JP": "Japan", "BR": "Brazil", "GB": "United Kingdom"}

    if not df_map.empty:
        df_map["country_name"] = df_map["country"].map(COUNTRY_NAMES)
        fig_map = px.choropleth(
            df_map, locations="country_name", locationmode="country names",
            color="avg_pop", color_continuous_scale=[[0, "#0d3320"], [0.5, "#1DB954"], [1, "#5eff8f"]],
            hover_name="country_name", hover_data={"avg_pop": True, "country_name": False}
        )
        fig_map.update_layout(
            **PLOTLY_THEME, height=300,
            geo=dict(bgcolor="#1a1a1a", showframe=False, showcoastlines=True,
                     coastlinecolor="#333333", showland=True, landcolor="#282828",
                     showocean=True, oceancolor="#121212"),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})

with c4:
    st.markdown('<p class="section-title">📊 Momentum Artistes</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Progression vs hier — vert = monte, rouge = descend</p>', unsafe_allow_html=True)

    if country == "Global":
        # On moyenne le momentum sur tous les pays pour avoir une vision mondiale
        df_mom = load("""
            SELECT artist_name, ROUND(AVG(momentum_score), 1) AS momentum_score
            FROM analytics.mart_artist_momentum
            GROUP BY artist_name
            ORDER BY momentum_score DESC
            LIMIT 8
        """)
    else:
        df_mom = load("""
            SELECT artist_name, momentum_score
            FROM analytics.mart_artist_momentum
            WHERE country = %(c)s
            ORDER BY momentum_score DESC
            LIMIT 8
        """, params={"c": country})

    if not df_mom.empty and df_mom["momentum_score"].abs().sum() > 0:
        colors_mom = ["#1DB954" if v >= 0 else "#e74c3c" for v in df_mom["momentum_score"]]
        fig5 = go.Figure(go.Bar(
            x=df_mom["momentum_score"], y=df_mom["artist_name"],
            orientation="h",
            marker=dict(color=colors_mom, line=dict(width=0)),
            text=df_mom["momentum_score"].round(1).astype(str),
            textposition="outside", textfont=dict(color="#FFFFFF", size=11),
        ))
        fig5.update_layout(**PLOTLY_THEME, height=300,
                           xaxis=dict(showgrid=True, gridcolor="#282828", zeroline=True, zerolinecolor="#555555"),
                           yaxis=dict(autorange="reversed", tickfont=dict(color="#FFFFFF", size=11)))
        st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown("""
        <div style='background:#1a1a1a;border-radius:8px;padding:30px;text-align:center;color:#b3b3b3;height:240px;display:flex;align-items:center;justify-content:center;flex-direction:column'>
        <span style='font-size:2em'>📅</span><br><br>
        Le momentum compare aujourd'hui vs hier.<br>
        <span style='font-size:0.85em'>Disponible après 2 jours de données pipeline.</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Ligne 3 : Heatmap inter-pays | Box plot ─────────────────────────────────────

c5, c6 = st.columns(2)

with c5:
    st.markdown('<p class="section-title">🌐 Présence mondiale des artistes</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Les 10 meilleurs artistes tous pays confondus — une case vide = absent de ce marché</p>', unsafe_allow_html=True)

    # On prend les 10 artistes avec la meilleure popularité moyenne sur l'ensemble des pays
    # puis on regarde leur score dans chaque pays individuellement
    df_heat = load("""
        WITH top_artistes AS (
            SELECT artist_name
            FROM staging.raw_tracks
            WHERE fetch_date = CURRENT_DATE
            GROUP BY artist_name
            ORDER BY AVG(popularity) DESC
            LIMIT 10
        )
        SELECT r.artist_name, r.country, ROUND(AVG(r.popularity), 1) AS avg_pop
        FROM staging.raw_tracks r
        JOIN top_artistes ON r.artist_name = top_artistes.artist_name
        WHERE r.fetch_date = CURRENT_DATE
        GROUP BY r.artist_name, r.country
    """)

    if not df_heat.empty:
        # On pivote le tableau : artistes en lignes, pays en colonnes
        df_pivot = df_heat.pivot(index="artist_name", columns="country", values="avg_pop")

        # On formate les valeurs : NaN (artiste absent) = case vide
        text_vals = [
            [f"{v:.0f}" if pd.notna(v) else "" for v in row]
            for row in df_pivot.values
        ]

        fig_heat = go.Figure(go.Heatmap(
            z=df_pivot.values,
            x=df_pivot.columns.tolist(),
            y=df_pivot.index.tolist(),
            colorscale=[[0, "#0d3320"], [0.5, "#1DB954"], [1, "#5eff8f"]],
            showscale=False,
            text=text_vals,
            texttemplate="%{text}",
            textfont=dict(size=12),
        ))
        fig_heat.update_layout(**PLOTLY_THEME, height=340,
                               xaxis=dict(tickfont=dict(color="#FFFFFF", size=13)),
                               yaxis=dict(tickfont=dict(color="#FFFFFF", size=11)))
        st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Pas encore assez de données.")

with c6:
    st.markdown('<p class="section-title">📦 Distribution des popularités</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Comment les scores sont répartis dans chaque pays — le pays sélectionné est mis en vert</p>', unsafe_allow_html=True)

    # On récupère toutes les popularités de la journée pour chaque pays
    df_box = load("SELECT country, popularity FROM staging.raw_tracks WHERE fetch_date = CURRENT_DATE")

    if not df_box.empty:
        fig_box = go.Figure()
        for c_name in COUNTRIES:
            subset = df_box[df_box["country"] == c_name]["popularity"]
            # Le pays choisi ressort en vert, les autres restent en gris
            couleur = "#1DB954" if (c_name == country or country == "Global") else "#444444"
            fig_box.add_trace(go.Box(
                y=subset,
                name=c_name,
                marker_color=couleur,
                line_color=couleur,
                boxmean=True,  # le trait en pointillé = la moyenne (pas juste la médiane)
            ))
        fig_box.update_layout(**PLOTLY_THEME, height=340, showlegend=False,
                              xaxis=dict(title="", tickfont=dict(color="#FFFFFF", size=13)),
                              yaxis=dict(title="Popularité", tickfont=dict(color="#b3b3b3"),
                                         gridcolor="#282828"))
        st.plotly_chart(fig_box, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Pas encore assez de données.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── Ligne 4 : Top Albums | Évolution temporelle ─────────────────────────────────

c7, c8 = st.columns(2)

with c7:
    label_pays = "dans le monde" if country == "Global" else f"en {country}"
    st.markdown('<p class="section-title">💿 Top 8 Albums</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="section-sub">Albums avec la meilleure popularité moyenne {label_pays} aujourd\'hui</p>', unsafe_allow_html=True)

    if country == "Global":
        df_albums = load("""
            SELECT album_name,
                   MIN(artist_name) AS artist_name,
                   ROUND(AVG(popularity), 1) AS avg_pop,
                   COUNT(DISTINCT track_id) AS nb_tracks,
                   ROW_NUMBER() OVER (ORDER BY AVG(popularity) DESC) AS rank
            FROM staging.raw_tracks
            WHERE fetch_date = CURRENT_DATE
            GROUP BY album_name
            ORDER BY avg_pop DESC
            LIMIT 8
        """)
    else:
        df_albums = load("""
            SELECT album_name,
                   MIN(artist_name) AS artist_name,
                   ROUND(AVG(popularity), 1) AS avg_pop,
                   COUNT(DISTINCT track_id) AS nb_tracks,
                   ROW_NUMBER() OVER (ORDER BY AVG(popularity) DESC) AS rank
            FROM staging.raw_tracks
            WHERE fetch_date = CURRENT_DATE AND country = %(c)s
            GROUP BY album_name
            ORDER BY avg_pop DESC
            LIMIT 8
        """, {"c": country})

    if not df_albums.empty:
        df_albums["label"] = df_albums["rank"].astype(str) + ". " + df_albums["album_name"].str[:18] + " · " + df_albums["artist_name"].str[:16]

        fig_alb = go.Figure(go.Bar(
            x=df_albums["avg_pop"],
            y=df_albums["label"],
            orientation="h",
            marker=dict(color="#1DB954", line=dict(width=0)),
            text=df_albums["avg_pop"].astype(str),
            textposition="outside",
            textfont=dict(color="#1DB954", size=11),
            customdata=df_albums["nb_tracks"],
            hovertemplate="<b>%{y}</b><br>Popularité : %{x}<br>Tracks dans le top : %{customdata}<extra></extra>",
        ))
        fig_alb.update_layout(**PLOTLY_THEME, height=340,
                              xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                              yaxis=dict(autorange="reversed", tickfont=dict(color="#FFFFFF", size=11)))
        st.plotly_chart(fig_alb, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Pas encore assez de données.")

with c8:
    st.markdown('<p class="section-title">📈 Évolution d\'un artiste dans le temps</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Popularité jour par jour — disponible après plusieurs jours de collecte</p>', unsafe_allow_html=True)

    # On charge la liste de tous les artistes présents en base pour le menu déroulant
    df_artists_list = load("SELECT DISTINCT artist_name FROM staging.raw_tracks ORDER BY artist_name")

    if not df_artists_list.empty:
        selected_artist = st.selectbox("Choisir un artiste", df_artists_list["artist_name"].tolist(), key="artist_timeline")

        if country == "Global":
            # Une ligne par pays pour voir si l'artiste performe différemment selon le marché
            df_timeline = load("""
                SELECT fetch_date, country, ROUND(AVG(popularity), 1) AS avg_pop
                FROM staging.raw_tracks
                WHERE artist_name = %(a)s
                GROUP BY fetch_date, country
                ORDER BY fetch_date
            """, {"a": selected_artist})
        else:
            # Une seule ligne pour le pays choisi
            df_timeline = load("""
                SELECT fetch_date, ROUND(AVG(popularity), 1) AS avg_pop
                FROM staging.raw_tracks
                WHERE artist_name = %(a)s AND country = %(c)s
                GROUP BY fetch_date
                ORDER BY fetch_date
            """, {"a": selected_artist, "c": country})

        if not df_timeline.empty and len(df_timeline) > 1:
            if country == "Global":
                fig_line = px.line(
                    df_timeline, x="fetch_date", y="avg_pop", color="country",
                    color_discrete_sequence=["#1DB954", "#17a347", "#5eff8f", "#0f6b2e", "#a8ffcd"],
                    markers=True,
                )
            else:
                fig_line = px.line(
                    df_timeline, x="fetch_date", y="avg_pop",
                    color_discrete_sequence=["#1DB954"],
                    markers=True,
                )
            fig_line.update_traces(line=dict(width=2.5))
            fig_line.update_layout(**PLOTLY_THEME, height=340,
                                   xaxis=dict(title="", tickfont=dict(color="#b3b3b3"), gridcolor="#282828"),
                                   yaxis=dict(title="Popularité", tickfont=dict(color="#b3b3b3"),
                                              gridcolor="#282828"))
            st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown("""
            <div style='background:#1a1a1a;border-radius:8px;padding:30px;text-align:center;color:#b3b3b3;height:240px;display:flex;align-items:center;justify-content:center;flex-direction:column'>
            <span style='font-size:2em'>📅</span><br><br>
            Ce graphique a besoin de plusieurs jours de données.<br>
            <span style='font-size:0.85em'>Reviens demain pour voir l'évolution !</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Lance le pipeline Airflow pour voir les données.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── Ligne 5 : Flux Kafka (pleine largeur) ──────────────────────────────────────

st.markdown('<p class="section-title">🔴 Flux Live — Streaming Kafka en temps réel</p>', unsafe_allow_html=True)
st.markdown('<p class="section-sub">Chaque ligne = un message reçu depuis le topic Kafka "spotify-tracks" via consumer.py → inséré dans analytics.live_feed</p>', unsafe_allow_html=True)

df_live = load("SELECT received_at, track_name, artist_name, country, popularity FROM analytics.live_feed ORDER BY received_at DESC LIMIT 15")

if not df_live.empty:
    col_stat, col_empty = st.columns([1, 3])
    with col_stat:
        st.metric("Messages reçus", len(df_live))
    st.dataframe(
        df_live.rename(columns={"received_at": "Reçu à", "track_name": "Track", "artist_name": "Artiste", "country": "Pays", "popularity": "Popularité"}),
        use_container_width=True, hide_index=True, height=200
    )
else:
    st.markdown("""
    <div style='background:#1a1a1a;border-radius:8px;padding:30px;text-align:center;color:#b3b3b3;'>
    ⏳ En attente de messages depuis Kafka...<br>
    <span style='font-size:0.85em'>Lance <code>python kafka/consumer.py</code> dans un terminal pour voir les données arriver ici.</span>
    </div>
    """, unsafe_allow_html=True)

col_btn, col_toggle = st.columns([1, 2])
with col_btn:
    if st.button("🔄 Rafraîchir le flux live"):
        st.rerun()
with col_toggle:
    auto_refresh = st.toggle("Auto-refresh toutes les 10s", value=False)

# ── Footer ──────────────────────────────────────────────────────────────────────

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align:center;color:#555555;font-size:0.75em;padding:8px'>
Spotify API → fetch_spotify.py → PostgreSQL staging → dbt models → Kafka → live_feed → ce dashboard<br>
Orchestré par <b style='color:#1DB954'>Apache Airflow</b> (toutes les heures) | ESILV M1 Data & IA — Projet ETL
</div>
""", unsafe_allow_html=True)
if auto_refresh:
    # st.rerun() relance Streamlit sans recharger le navigateur, donc le toggle garde son état
    time.sleep(10)
    st.rerun()
