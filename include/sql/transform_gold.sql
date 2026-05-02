CREATE OR REPLACE PROCEDURE sp_refresh_gold_metrics()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Limpa os dados agregados antigos (Truncate é mais performático que Delete)
    TRUNCATE TABLE gold_taxi_metrics;

    -- Insere a nova agregação baseada na camada Silver[cite: 2]
    INSERT INTO gold_taxi_metrics (
        vendor_id,
        vendor_name,
        hour_of_day,
        payment_label,
        day_of_week,

        total_trips,
        total_revenue,

        avg_fare,
        avg_distance,

        avg_tip_amount,
        avg_tip_pct,

        avg_duration,
        avg_speed,
        
        updated_at
    )
    SELECT
        vendor_id,
        CASE vendor_id
            WHEN 1 THEN 'Creative Mobile'
            WHEN 2 THEN 'VeriFone'
            ELSE 'Outro'
        END AS vendor_name,
        hour_of_day,
        CASE payment_type
            WHEN 1 THEN 'Cartao de Credito'
            WHEN 2 THEN 'Dinheiro'
            WHEN 3 THEN 'Sem Cobranca'
            WHEN 4 THEN 'Disputa'
            WHEN 5 THEN 'Desconhecido'
            WHEN 6 THEN 'Cancelada'
            ELSE 'Outro'
        END AS payment_label,

        day_of_week,

        COUNT(*) as total_trips,
        SUM(total_amount) as total_revenue,
        
        AVG(fare_amount) as avg_fare,
        AVG(trip_distance) as avg_distance,

        AVG(tip_amount) AS avg_tip_amount,
        AVG(tip_pct) as avg_tip_pct,

        AVG(trip_duration_min) AS avg_duration,
        AVG(trip_speed_mph) AS avg_speed,

        -- AVG(tip_amount) as avg_tip,
        -- AVG(tip_amount) as avg_tip_amount,
        CURRENT_TIMESTAMP
    FROM silver_taxi_trips
    GROUP BY 
        vendor_id,
        hour_of_day,
        payment_type,
        day_of_week
    ORDER BY hour_of_day;
END;
$$;