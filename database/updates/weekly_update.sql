-- Weekly update main function
CREATE OR REPLACE FUNCTION perform_weekly_update() RETURNS void AS $$
DECLARE
    v_start_time TIMESTAMPTZ;
    v_log_id INTEGER;
    v_processed INTEGER := 0;
    v_error TEXT;
BEGIN
    v_start_time := CURRENT_TIMESTAMP;
    
    -- Create log entry
    INSERT INTO update_logs (update_type, start_time, status)
    VALUES ('WEEKLY', v_start_time, 'RUNNING')
    RETURNING id INTO v_log_id;

    BEGIN
        -- 1. Update CTMIS view
        PERFORM update_streamlit_view();
        
        -- 2. Generate weekly summary stats
        INSERT INTO weekly_summary_stats (
            report_date,
            total_active_trials,
            trials_by_phase,
            trials_by_disease,
            avg_market_values,
            high_value_opportunities
        )
        SELECT
            CURRENT_DATE,
            (SELECT COUNT(*) FROM streamlit_ctmis_view),
            jsonb_object_agg(phase, count) FROM (
                SELECT phase, COUNT(*) 
                FROM streamlit_ctmis_view 
                GROUP BY phase
            ) t,
            jsonb_object_agg(disease_area, count) FROM (
                SELECT disease_area, COUNT(*) 
                FROM streamlit_ctmis_view 
                GROUP BY disease_area
            ) d,
            jsonb_object_agg(disease_area, avg_value) FROM (
                SELECT 
                    disease_area, 
                    ROUND(AVG(estimated_market_value)/1000000, 2) as avg_value
                FROM streamlit_ctmis_view 
                GROUP BY disease_area
            ) v,
            (SELECT json_agg(row_to_json(t)) 
             FROM (
                SELECT 
                    nct_id, 
                    brief_title, 
                    disease_area, 
                    phase,
                    ROUND(estimated_market_value/1000000, 2) as value_millions,
                    ROUND(expected_return/1000000, 2) as return_millions
                FROM streamlit_ctmis_view
                WHERE expected_return > 0
                ORDER BY expected_return DESC
                LIMIT 10
             ) t
            );

        -- 3. Generate disease area alerts
        INSERT INTO disease_area_alerts (
            alert_date,
            disease_area,
            alert_type,
            alert_message,
            metric_value
        )
        SELECT 
            CURRENT_DATE,
            disease_area,
            'VALUE_CHANGE',
            'Significant value change detected',
            (new_value - old_value) / old_value * 100
        FROM (
            SELECT 
                d1.disease_area,
                d1.avg_value as new_value,
                d2.avg_value as old_value
            FROM 
                (SELECT 
                    disease_area, 
                    AVG(estimated_market_value) as avg_value 
                FROM streamlit_ctmis_view 
                GROUP BY disease_area) d1
            JOIN 
                (SELECT 
                    disease_area, 
                    AVG(estimated_market_value) as avg_value 
                FROM streamlit_ctmis_view 
                WHERE last_updated < CURRENT_DATE - INTERVAL '7 days'
                GROUP BY disease_area) d2
            ON d1.disease_area = d2.disease_area
            WHERE ABS((d1.avg_value - d2.avg_value) / d2.avg_value) > 0.20
        ) value_changes;

        -- Record success
        UPDATE update_logs 
        SET 
            end_time = CURRENT_TIMESTAMP,
            status = 'SUCCESS',
            records_processed = v_processed
        WHERE id = v_log_id;

    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_error = MESSAGE_TEXT;
        
        -- Record error
        UPDATE update_logs 
        SET 
            end_time = CURRENT_TIMESTAMP,
            status = 'ERROR',
            error_message = v_error
        WHERE id = v_log_id;
        
        RAISE NOTICE 'Error in weekly update: %', v_error;
    END;
END;
$$ LANGUAGE plpgsql;
