-- DDL para a tabela Gold
CREATE TABLE IF NOT EXISTS gold_taxi_metrics (
    vendor_id INT,
    vendor_name TEXT,
    hour_of_day INT,

    payment_label TEXT,
    day_of_week TEXT,

    total_trips BIGINT,
    total_revenue NUMERIC,

    avg_fare NUMERIC,
    avg_distance NUMERIC,
    
    avg_tip_amount NUMERIC,
    avg_tip_pct NUMERIC,

    avg_duration NUMERIC,
    avg_speed NUMERIC,

    -- avg_tip FLOAT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (vendor_id, hour_of_day, payment_label, day_of_week, updated_at)
);