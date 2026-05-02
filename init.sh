#!/bin/bash
set -e
set -x

echo "⏳ Waiting Postgres..."

until airflow db check; do
  echo "waiting postgres..."
  sleep 3
done

echo "🔄 Running Airflow DB migrations..."
airflow db migrate

echo "👤 Creating admin user..."
airflow users create \
  --username admin \
  --password admin \
  --firstname admin \
  --lastname user \
  --role Admin \
  --email admin@email.com || true

echo "🔌 Creating connection postgres_nyc..."

airflow connections delete postgres_nyc || true
airflow connections add postgres_nyc \
  --conn-type postgres \
  --conn-host postgres \
  --conn-login postgres \
  --conn-password postgres \
  --conn-schema nyc_yellow_taxi \
  --conn-port 5432

echo "✅ Init completed successfully"