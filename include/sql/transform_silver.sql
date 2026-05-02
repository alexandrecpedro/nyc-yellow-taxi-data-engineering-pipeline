-- Procedure para mover da Bronze (Raw) para Silver (Clean/Typed)
CREATE OR REPLACE PROCEDURE sp_transform_bronze_to_silver()
LANGUAGE plpgsql
AS $$
BEGIN
    TRUNCATE TABLE silver_taxi_trips;

    INSERT INTO silver_taxi_trips (
        vendor_id,
        pickup_datetime,
        dropoff_datetime,
        payment_type,
        day_of_week,
        hour_of_day,
        trip_distance,
        fare_amount,
        tip_amount,
        total_amount,
        trip_duration_min,
        tip_pct,
        trip_speed_mph
    )
    SELECT
        NULLIF(TRIM(vendor_id), '')::INT,
        NULLIF(TRIM(tpep_pickup_datetime), '')::TIMESTAMP,
        NULLIF(TRIM(tpep_dropoff_datetime), '')::TIMESTAMP,
        NULLIF(TRIM(payment_type), '')::INT,
        -- INITCAP(TO_CHAR(NULLIF(TRIM(tpep_pickup_datetime), '')::TIMESTAMP, 'FMDay')),
        CASE EXTRACT(DOW FROM tpep_pickup_datetime::TIMESTAMP)
            WHEN 0 THEN 'Domingo'
            WHEN 1 THEN 'Segunda-feira'
            WHEN 2 THEN 'Terca-feira'
            WHEN 3 THEN 'Quarta-feira'
            WHEN 4 THEN 'Quinta-feira'
            WHEN 5 THEN 'Sexta-feira'
            WHEN 6 THEN 'Sabado'
        END,
        EXTRACT(HOUR FROM NULLIF(TRIM(tpep_pickup_datetime), '')::TIMESTAMP)::INT,
        NULLIF(TRIM(trip_distance), '')::FLOAT,
        NULLIF(TRIM(fare_amount), '')::FLOAT,
        NULLIF(TRIM(tip_amount), '')::FLOAT,
        NULLIF(TRIM(total_amount), '')::FLOAT,
        -- Cálculo de duração direto no SQL
        EXTRACT(EPOCH FROM (
            NULLIF(TRIM(tpep_dropoff_datetime), '')::TIMESTAMP
            - NULLIF(TRIM(tpep_pickup_datetime), '')::TIMESTAMP
        )) / 60,
        -- Cálculo da % de gorjeta sobre o valor da tarifa (fare)
        CASE
            WHEN NULLIF(TRIM(fare_amount), '')::FLOAT > 0 THEN
                (NULLIF(TRIM(tip_amount), '')::FLOAT / NULLIF(TRIM(fare_amount), '')::FLOAT) * 100
            ELSE 0
        END,
        CASE
            WHEN EXTRACT(EPOCH FROM (
                NULLIF(TRIM(tpep_dropoff_datetime), '')::TIMESTAMP
                - NULLIF(TRIM(tpep_pickup_datetime), '')::TIMESTAMP
            )) > 0 THEN
                NULLIF(TRIM(trip_distance), '')::FLOAT * 3600.0
                /
                EXTRACT(EPOCH FROM (
                    NULLIF(TRIM(tpep_dropoff_datetime), '')::TIMESTAMP
                    - NULLIF(TRIM(tpep_pickup_datetime), '')::TIMESTAMP
                ))
            ELSE NULL
        END
    FROM bronze_taxi_trips
    WHERE 
        NULLIF(TRIM(trip_distance), '')::FLOAT > 0
        AND NULLIF(TRIM(fare_amount), '')::FLOAT > 0
        AND NULLIF(TRIM(tpep_pickup_datetime), '') IS NOT NULL
        AND NULLIF(TRIM(tpep_dropoff_datetime), '') IS NOT NULL
        AND NULLIF(TRIM(tpep_dropoff_datetime), '')::TIMESTAMP
            > NULLIF(TRIM(tpep_pickup_datetime), '')::TIMESTAMP;
        -- AND total_amount::FLOAT > 0
        -- AND tpep_dropoff_datetime::TIMESTAMP > tpep_pickup_datetime::TIMESTAMP
        -- AND passenger_count::INT > 0;
END;
$$;