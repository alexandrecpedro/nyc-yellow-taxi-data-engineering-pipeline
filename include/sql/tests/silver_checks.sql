-- Sem valores negativos
SELECT COUNT(*) = 0 FROM silver_taxi_trips WHERE trip_distance < 0;

-- Datas válidas
SELECT COUNT(*) = 0 FROM silver_taxi_trips WHERE dropoff_datetime < pickup_datetime;

-- Receita válida
SELECT COUNT(*) > 0 FROM gold_taxi_metrics;