from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.common.sql.operators.sql import SQLCheckOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta

import logging
import os

# ================================
# CONFIG
# ================================

FILE_PATH = Variable.get(
    "NYC_TAXI_FILE_PATH",
    default_var="/opt/airflow/include/data/bronze/yellow_tripdata_2016-03.csv"
)

default_args = {
    'owner': 'alexandre',
    'depends_on_past': False,
    'start_date': datetime(year=2024, month=1, day=1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=30),
}

# ================================
# BRONZE LOAD (ROBUSTO)
# ================================

def load_bronze():
    logging.info(f"Iniciando ingestão: {FILE_PATH}")

    if not os.path.exists(FILE_PATH):
        raise FileNotFoundError(f"Arquivo não encontrado: {FILE_PATH}")

    pg_hook = PostgresHook(postgres_conn_id='postgres_nyc')
    # Usando o hook para obter a conexão
    conn = pg_hook.get_conn()

    try:
        with conn.cursor() as cursor:
             # (A) staging table (evita perder dados)
            logging.info("Criando tabela temporária...")
            cursor.execute("""
                CREATE TEMP TABLE bronze_tmp (
                    LIKE bronze_taxi_trips INCLUDING ALL
                ) ON COMMIT DROP;
            """)

            # (B) load seguro
            with open(FILE_PATH, 'r', encoding='utf-8') as f:
                logging.info("Executando COPY...")
                cursor.copy_expert("""
                    COPY bronze_tmp(
                        vendor_id,
                        tpep_pickup_datetime,
                        tpep_dropoff_datetime,
                        passenger_count,
                        trip_distance,
                        pickup_longitude,
                        pickup_latitude,
                        rate_code_id,
                        store_and_fwd_flag,
                        dropoff_longitude,
                        dropoff_latitude,
                        payment_type,
                        fare_amount,
                        extra,
                        mta_tax,
                        tip_amount,
                        tolls_amount,
                        improvement_surcharge,
                        total_amount
                    )
                    FROM STDIN
                    WITH (
                        FORMAT CSV,
                        HEADER TRUE,
                        DELIMITER ',',
                        NULL '',
                        ENCODING 'UTF8'
                    )
                """, f)
            
            # (C) replace seguro
            logging.info("Atualizando tabela bronze...")
            cursor.execute("TRUNCATE TABLE bronze_taxi_trips;")
            cursor.execute("""
                INSERT INTO bronze_taxi_trips
                SELECT * FROM bronze_tmp;
            """)

            conn.commit()
            logging.info("Carga bronze finalizada com sucesso!")
    except Exception as e:
        conn.rollback()
        logging.error(f"Erro na carga bronze: {e}")
        raise

    finally:
        conn.close()

# ================================
# DAG
# ================================

with DAG(
    'nyc_yellow_taxi_pipeline',
    default_args=default_args,
    # schedule='@monthly',
    schedule=None,
    catchup=False,
    tags=['bronze', 'silver', 'gold'],
    # template_searchpath=['/usr/local/airflow/include/sql']
    template_searchpath=['/opt/airflow/include/sql']
) as dag:
    # 1. Setup: Cria tabelas e as duas novas Procedures separadas
    setup_tables = SQLExecuteQueryOperator(
        task_id='setup_tables',
        conn_id='postgres_nyc',
        sql=[
            'bronze_taxi_trips.sql',
            'silver_taxi_trips.sql',
            'gold_taxi_metrics.sql',
        ]
    )

    setup_procedures = SQLExecuteQueryOperator(
        task_id='setup_procedures',
        conn_id='postgres_nyc',
        sql=[
            'transform_silver.sql',
            'transform_gold.sql'
        ]
    )

    # 2. Ingestão (Bronze)
    ingest_bronze = PythonOperator(
        task_id='ingest_bronze',
        python_callable=load_bronze,
        retries=3,
        retry_delay=timedelta(minutes=2)
    )

    # 3. Data Quality Bronze
    check_bronze = SQLCheckOperator(
        task_id='check_bronze_not_empty',
        conn_id='postgres_nyc',
        sql="SELECT COUNT(*) > 0 FROM bronze_taxi_trips;"
    )

    # 4. Transformação Silver (Procedure 1)
    transform_silver = SQLExecuteQueryOperator(
        task_id='transform_silver',
        conn_id='postgres_nyc',
        sql="CALL sp_transform_bronze_to_silver();"
    )

    # 5. Data Quality Silver
    check_silver = SQLCheckOperator(
        task_id='check_silver_not_empty',
        conn_id='postgres_nyc',
        sql="SELECT COUNT(*) > 0 FROM silver_taxi_trips;"
    )

    # 6. Transformação Gold (Procedure 2)
    transform_gold = SQLExecuteQueryOperator(
        task_id='refresh_gold',
        conn_id='postgres_nyc',
        sql="CALL sp_refresh_gold_metrics();"
    )

    # 7. Data Quality Gold
    check_gold = SQLCheckOperator(
        task_id='check_gold_not_empty',
        conn_id='postgres_nyc',
        sql="SELECT COUNT(*) > 0 FROM gold_taxi_metrics;"
    )

    # ================================
    # ORQUESTRAÇÃO
    # ================================
    
    setup_tables >> setup_procedures >> ingest_bronze >> check_bronze >> transform_silver >> check_silver >> transform_gold >> check_gold