CREATE OR REPLACE VIEW sponsor_portfolio_summary AS
SELECT 
    sponsor_name,
    COUNT(*) as total_trials,
    COUNT(CASE WHEN status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING') THEN 1 END) as active_trials,
    COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_trials,
    ARRAY_AGG(DISTINCT EXTRACT(YEAR FROM completion_date)) as trial_years,
    COUNT(DISTINCT determine_disease_area(conditions)) as unique_diseases,
    COUNT(DISTINCT phase) as unique_phases,
    JSONB_OBJECT_AGG(phase, COUNT(*)) FILTER (WHERE phase IS NOT NULL) as trials_per_phase,
    ROUND(SUM(CASE 
        WHEN status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING') 
        THEN COALESCE(estimated_market_value, 0) 
        ELSE 0 
    END)/1000000, 2) as active_portfolio_value_millions,
    ROUND(AVG(CASE 
        WHEN status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING') 
        THEN phase_success_probability 
    END), 3) as avg_success_probability
FROM streamlit_ctmis_view
GROUP BY sponsor_name;
