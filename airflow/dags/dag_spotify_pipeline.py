"""
dag_spotify_pipeline.py
Orchestre le pipeline complet toutes les heures :
1. Ingestion depuis l'API Spotify
2. Transformations dbt
3. Publication dans Kafka
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import sys

sys.path.insert(0, "/opt/airflow/ingestion")
sys.path.insert(0, "/opt/airflow/kafka")

default_args = {
    "owner": "chrisa",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 6, 16),
}

with DAG(
    dag_id="spotify_pipeline",
    default_args=default_args,
    schedule_interval="@hourly",
    catchup=False,
    description="Pipeline complet : Spotify API → PostgreSQL → dbt → Kafka",
) as dag:

    def ingest():
        from fetch_spotify import run
        run()

    def publish():
        from producer import run
        run()

    task_ingest = PythonOperator(
        task_id="fetch_spotify_data",
        python_callable=ingest,
    )

    task_dbt = BashOperator(
        task_id="run_dbt_models",
        bash_command="cd /opt/airflow/dbt_project && pip install dbt-postgres --quiet && dbt run --profiles-dir .",
    )

    task_kafka = PythonOperator(
        task_id="publish_to_kafka",
        python_callable=publish,
    )

    task_ingest >> task_dbt >> task_kafka
