-- Function to calculate phase success probability and LOA
CREATE OR REPLACE FUNCTION calculate_success_probabilities(
    p_disease_area VARCHAR,
    p_phase VARCHAR
) RETURNS TABLE (
    phase_success_probability DECIMAL,
    likelihood_of_approval DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE p_phase 
            WHEN 'PHASE1' THEN hp.phase_1_to_2
            WHEN 'PHASE2' THEN hp.phase_2_to_3
            WHEN 'PHASE3' THEN hp.phase_3_to_nda_bla
            WHEN 'FDA_REVIEW' THEN hp.nda_bla_to_approval
            ELSE hp.phase_1_to_2 -- Default to phase 1 probability
        END AS phase_success_probability,
        hp.loa_from_current_phase AS likelihood_of_approval
    FROM disease_areas da
    LEFT JOIN hay_probabilities hp ON hp.disease_area_id = da.id
    WHERE da.area_name = p_disease_area
    UNION ALL
    SELECT 
        0.632 AS phase_success_probability, -- Average phase success
        0.112 AS likelihood_of_approval     -- Average LOA
    WHERE NOT EXISTS (
        SELECT 1 
        FROM disease_areas da 
        WHERE da.area_name = p_disease_area
    );
END;
$$ LANGUAGE plpgsql;

-- Function to calculate cumulative probability of success
CREATE OR REPLACE FUNCTION calculate_cumulative_probability(
    p_disease_area VARCHAR,
    p_start_phase VARCHAR
) RETURNS DECIMAL AS $$
DECLARE
    v_probability DECIMAL;
BEGIN
    SELECT 
        CASE p_start_phase
            WHEN 'PHASE1' THEN hp.phase_1_to_2 * hp.phase_2_to_3 * hp.phase_3_to_nda_bla * hp.nda_bla_to_approval
            WHEN 'PHASE2' THEN hp.phase_2_to_3 * hp.phase_3_to_nda_bla * hp.nda_bla_to_approval
            WHEN 'PHASE3' THEN hp.phase_3_to_nda_bla * hp.nda_bla_to_approval
            WHEN 'FDA_REVIEW' THEN hp.nda_bla_to_approval
            ELSE 0.112 -- Default average probability
        END INTO v_probability
    FROM disease_areas da
    LEFT JOIN hay_probabilities hp ON hp.disease_area_id = da.id
    WHERE da.area_name = p_disease_area;

    RETURN COALESCE(v_probability, 0.112);
END;
$$ LANGUAGE plpgsql;
