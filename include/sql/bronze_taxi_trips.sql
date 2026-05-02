-- Camada Bronze atualizada para o layout de 2016
CREATE TABLE IF NOT EXISTS bronze_taxi_trips (
    vendor_id TEXT,
    tpep_pickup_datetime TEXT,
    tpep_dropoff_datetime TEXT,
    passenger_count TEXT,
    trip_distance TEXT,
    pickup_longitude TEXT,   -- Coluna faltante 1
    pickup_latitude TEXT,    -- Coluna faltante 2
    rate_code_id TEXT,
    store_and_fwd_flag TEXT,
    dropoff_longitude TEXT,  -- Coluna faltante 3
    dropoff_latitude TEXT,   -- Coluna faltante 4
    payment_type TEXT,
    fare_amount TEXT,
    extra TEXT,
    mta_tax TEXT,
    tip_amount TEXT,
    tolls_amount TEXT,
    improvement_surcharge TEXT,
    total_amount TEXT,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);