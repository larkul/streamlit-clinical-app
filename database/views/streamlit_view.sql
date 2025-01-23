DROP VIEW IF EXISTS streamlit_ctmis_view CASCADE;

CREATE VIEW streamlit_ctmis_view AS
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
    ) AS has_biomarker,
    ct.study_type,
    CASE ct.phase
        WHEN 'PHASE1' THEN hp.phase_1_to_2
        WHEN 'PHASE2' THEN hp.phase_2_to_3
        WHEN 'PHASE3' THEN hp.phase_3_to_nda_bla
        ELSE NULL
    END AS phase_success_probability,
    hp.loa_from_current_phase AS likelihood_of_approval,
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
    ) AS market_reaction_level,
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
    ) AS estimated_market_value,
    calculate_development_costs(
        ct.phase,
        da.area_name
    ) AS estimated_development_cost,
    (calculate_market_value(
        da.area_name,
        ct.phase
    ) * COALESCE(hp.loa_from_current_phase, 0.1) * (1 + (1.0 / dar.rank))) - 
    calculate_development_costs(
        ct.phase,
        da.area_name
    ) AS expected_return
FROM 
    consolidated_clinical_trials ct
CROSS JOIN LATERAL get_company_classification(ct.sponsor_name) cc
LEFT JOIN disease_areas da ON determine_disease_area(ct.conditions) = da.area_name
LEFT JOIN disease_area_ranking dar ON da.area_name = dar.area_name
LEFT JOIN hay_probabilities hp ON hp.disease_area_id = da.id
WHERE 
    ct.phase IN ('PHASE1', 'PHASE2', 'PHASE3')  -- Only include Phase 1, 2, and 3
    AND ct.status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING');

