-- Drop existing view if exists
DROP TABLE IF EXISTS streamlit_ctmis_view CASCADE;

-- Create the Streamlit CTMIS view
CREATE TABLE streamlit_ctmis_view (
    id SERIAL PRIMARY KEY,
    nct_id VARCHAR NOT NULL,
    brief_title TEXT,
    sponsor_name VARCHAR,
    disease_area VARCHAR(100),
    disease_rank INT,
    phase VARCHAR,
    status VARCHAR,
    completion_date DATE,
    company_size VARCHAR(50),
    company_type VARCHAR(50),
    has_biomarker BOOLEAN,
    study_design VARCHAR(100),
    phase_success_probability DECIMAL(10,4),
    likelihood_of_approval DECIMAL(10,4),
    ctmis_score DECIMAL(10,4),
    market_reaction_level VARCHAR(20),
    market_reaction_strength VARCHAR(20),
    estimated_market_value DECIMAL(15,2),
    estimated_development_cost DECIMAL(15,2),
    expected_return DECIMAL(15,2),
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create update function for the view
CREATE OR REPLACE FUNCTION update_streamlit_view() RETURNS void AS $$
BEGIN
    -- Clear existing data
    TRUNCATE TABLE streamlit_ctmis_view;

    -- Insert updated data
    INSERT INTO streamlit_ctmis_view (
        nct_id, brief_title, sponsor_name, disease_area, disease_rank, phase, 
        status, completion_date, company_size, company_type, has_biomarker, 
        study_design, phase_success_probability, likelihood_of_approval,
        ctmis_score, market_reaction_level, market_reaction_strength,
        estimated_market_value, estimated_development_cost, expected_return
    )
    SELECT 
        ct.nct_id,
        ct.brief_title,
        ct.sponsor_name,
        da.area_name AS disease_area,
        dar.rank AS disease_rank,
        ct.phase,
        ct.status,
        ct.completion_date::DATE,
        cc.company_size,
        cc.company_type,
        has_biomarker_indicators(
            ct.eligibility_criteria,
            ct.outcome_measures,
            ct.design_info,
            ct.biospec_retention,
            ct.biospec_description
        ),
        ct.study_type,
        CASE ct.phase
            WHEN 'PHASE1' THEN hp.phase_1_to_2
            WHEN 'PHASE2' THEN hp.phase_2_to_3
            WHEN 'PHASE3' THEN hp.phase_3_to_nda_bla
            ELSE NULL
        END,
        hp.loa_from_current_phase,
        calculate_market_reaction_ctmis(
            cc.company_size,
            ct.phase,
            da.area_name,
            ct.study_type,
            ct.design_info
        ) * (1 + (1.0 / dar.rank)) AS ctmis_score,
        get_market_reaction_level(
            calculate_market_reaction_ctmis(
                cc.company_size,
                ct.phase,
                da.area_name,
                ct.study_type,
                ct.design_info
            )
        ),
        CASE 
            WHEN calculate_market_reaction_ctmis(
                cc.company_size,
                ct.phase,
                da.area_name,
                ct.study_type,
                ct.design_info
            ) >= 7.5 THEN 'Strong'
            WHEN calculate_market_reaction_ctmis(
                cc.company_size,
                ct.phase,
                da.area_name,
                ct.study_type,
                ct.design_info
            ) >= 5.0 THEN 'Moderate'
            ELSE 'Weak'
        END AS market_reaction_strength,
        calculate_market_value(
            da.area_name,
            ct.phase
        ),
        calculate_development_costs(
            ct.phase,
            da.area_name
        ),
        (calculate_market_value(
            da.area_name,
            ct.phase
        ) * COALESCE(hp.loa_from_current_phase, 0.1) * (1 + (1.0 / dar.rank))) - 
        calculate_development_costs(
            ct.phase,
            da.area_name
        )
    FROM consolidated_clinical_trials ct
    CROSS JOIN LATERAL get_company_classification(ct.sponsor_name) cc
    LEFT JOIN disease_areas da ON determine_disease_area(ct.conditions) = da.area_name
    LEFT JOIN disease_area_ranking dar ON da.area_name = dar.area_name
    LEFT JOIN hay_probabilities hp ON hp.disease_area_id = da.id
    WHERE status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING');

    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_ctmis_reaction_strength ON streamlit_ctmis_view(market_reaction_strength);
    CREATE INDEX IF NOT EXISTS idx_ctmis_disease ON streamlit_ctmis_view(disease_area);
    CREATE INDEX IF NOT EXISTS idx_ctmis_phase ON streamlit_ctmis_view(phase);
    CREATE INDEX IF NOT EXISTS idx_ctmis_value ON streamlit_ctmis_view(estimated_market_value DESC);
END;
$$ LANGUAGE plpgsql;
