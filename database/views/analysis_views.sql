-- Disease area summary
CREATE OR REPLACE VIEW disease_area_summary AS
SELECT 
    disease_area,
    COUNT(*) as trial_count,
    ROUND(AVG(phase_success_probability), 2) as avg_phase_success,
    ROUND(AVG(likelihood_of_approval), 2) as avg_loa,
    ROUND(AVG(ctmis_score), 2) as avg_ctmis,
    ROUND(AVG(estimated_market_value)/1000000, 2) as avg_value_millions,
    ROUND(AVG(estimated_development_cost)/1000000, 2) as avg_cost_millions,
    ROUND(AVG(expected_return)/1000000, 2) as avg_return_millions,
    COUNT(CASE WHEN has_biomarker THEN 1 END) as biomarker_trials,
    COUNT(DISTINCT sponsor_name) as unique_sponsors
FROM streamlit_ctmis_view
GROUP BY disease_area
ORDER BY avg_value_millions DESC;

-- Company size analysis
CREATE OR REPLACE VIEW company_size_summary AS
SELECT 
    company_size,
    company_type,
    COUNT(*) as trial_count,
    ROUND(AVG(ctmis_score), 2) as avg_ctmis,
    ROUND(AVG(estimated_market_value)/1000000, 2) as avg_value_millions,
    ROUND(AVG(estimated_development_cost)/1000000, 2) as avg_cost_millions,
    COUNT(CASE WHEN has_biomarker THEN 1 END) as biomarker_trials,
    COUNT(DISTINCT sponsor_name) as unique_sponsors
FROM streamlit_ctmis_view
GROUP BY company_size, company_type
ORDER BY avg_value_millions DESC;

-- Phase analysis
CREATE OR REPLACE VIEW phase_summary AS
SELECT 
    phase,
    COUNT(*) as trial_count,
    ROUND(AVG(phase_success_probability), 2) as avg_phase_success,
    ROUND(AVG(likelihood_of_approval), 2) as avg_loa,
    ROUND(AVG(ctmis_score), 2) as avg_ctmis,
    ROUND(AVG(estimated_market_value)/1000000, 2) as avg_value_millions,
    ROUND(AVG(estimated_development_cost)/1000000, 2) as avg_cost_millions,
    COUNT(CASE WHEN has_biomarker THEN 1 END) as biomarker_trials
FROM streamlit_ctmis_view
GROUP BY phase
ORDER BY avg_value_millions DESC;

-- Top value opportunities
CREATE OR REPLACE VIEW top_opportunities AS
SELECT 
    nct_id,
    brief_title,
    sponsor_name,
    disease_area,
    phase,
    company_size,
    ROUND(estimated_market_value/1000000, 2) as value_millions,
    ROUND(estimated_development_cost/1000000, 2) as cost_millions,
    ROUND(expected_return/1000000, 2) as return_millions,
    ROUND(likelihood_of_approval * 100, 1) as success_probability,
    has_biomarker,
    ctmis_score
FROM streamlit_ctmis_view
WHERE expected_return > 0
ORDER BY expected_return DESC
LIMIT 100;
