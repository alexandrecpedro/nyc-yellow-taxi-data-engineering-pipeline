-- Camada Silver: Dados tipados e filtrados
CREATE TABLE IF NOT EXISTS silver_taxi_trips (
    id SERIAL,
    vendor_id INT,
    pickup_datetime TIMESTAMP,
    dropoff_datetime TIMESTAMP,

    payment_type INT,
    day_of_week TEXT,
    hour_of_day INT,

    trip_distance FLOAT,
    fare_amount FLOAT,
    tip_amount FLOAT,
    total_amount FLOAT,

    trip_duration_min FLOAT,
    tip_pct FLOAT,
    trip_speed_mph FLOAT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, pickup_datetime)
);