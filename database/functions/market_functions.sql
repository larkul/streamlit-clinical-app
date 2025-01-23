-- Market Value Calculation
CREATE OR REPLACE FUNCTION calculate_market_value(
    p_disease_area VARCHAR,
    p_phase VARCHAR
) RETURNS DECIMAL AS $$
DECLARE
    v_base_value_approval DECIMAL := 1620.0;  -- $1.62B in millions at approval
    v_base_value_discovery DECIMAL := 64.3;   -- $64.3M at discovery
    v_discount_rate DECIMAL := 0.1;           -- 10% annual discount rate

    v_disease_multiplier DECIMAL;
    v_phase_multiplier DECIMAL;
    v_transition_probability DECIMAL;
    v_years_to_approval INT;
BEGIN
    SELECT
        CASE p_disease_area
            WHEN 'AUTOIMMUNE' THEN 3.0
            WHEN 'RARE_DISEASES' THEN 8.0
            WHEN 'ENDOCRINE' THEN 2.5
            WHEN 'ONCOLOGY' THEN 2.7
            WHEN 'CARDIOVASCULAR' THEN 1.8
            WHEN 'NEUROLOGY' THEN 2.0
            WHEN 'CNS' THEN 2.0
            WHEN 'RESPIRATORY' THEN 1.6
            WHEN 'GENITOURINARY' THEN 1.3
            WHEN 'OPHTHALMOLOGY' THEN 1.2
            WHEN 'INFECTIOUS_DISEASE' THEN 1.0
            WHEN 'VACCINES' THEN 0.9
            ELSE 1.0
        END INTO v_disease_multiplier;

    SELECT
        CASE p_phase
            WHEN 'DISCOVERY' THEN 0.04
            WHEN 'PHASE1' THEN 0.15
            WHEN 'PHASE2' THEN 0.30
            WHEN 'PHASE3' THEN 0.60
            WHEN 'FDA_REVIEW' THEN 0.85
            WHEN 'APPROVED' THEN 1.0
            ELSE 0.05
        END INTO v_phase_multiplier;

    IF p_phase = 'DISCOVERY' THEN
        v_transition_probability := 0.5;
        v_years_to_approval := 10;
    ELSIF p_phase = 'PHASE1' THEN
        v_transition_probability := 0.51;
        v_years_to_approval := 8;
    ELSIF p_phase = 'PHASE2' THEN
        v_transition_probability := 0.31;
        v_years_to_approval := 6;
    ELSIF p_phase = 'PHASE3' THEN
        v_transition_probability := 0.11;
        v_years_to_approval := 3;
    ELSIF p_phase = 'FDA_REVIEW' THEN
        v_transition_probability := 0.85;
        v_years_to_approval := 1;
    ELSIF p_phase = 'APPROVED' THEN
        v_transition_probability := 1.0;
        v_years_to_approval := 0;
    ELSE
        v_transition_probability := 0.05;  -- Default for unknown phases
        v_years_to_approval := 12;
    END IF;

    RETURN (
        v_base_value_approval *
        v_disease_multiplier *
        v_phase_multiplier *
        v_transition_probability /
        POWER((1 + v_discount_rate), v_years_to_approval)
    );
END;
$$ LANGUAGE plpgsql;

-- Market Reaction CTMIS Calculation
CREATE OR REPLACE FUNCTION calculate_market_reaction_ctmis(
    p_company_size VARCHAR,
    p_phase VARCHAR,
    p_disease_area VARCHAR,
    p_study_type VARCHAR,
    p_design_info JSONB,
    p_eligibility JSONB,
    p_outcomes JSONB,
    p_biospec_retention TEXT,
    p_biospec_description TEXT
) RETURNS DECIMAL AS $$
DECLARE
    v_base_score DECIMAL := 5.0;
    v_company_multiplier DECIMAL;
    v_market_reaction DECIMAL;
    v_design_bonus DECIMAL := 0.0;
    v_design_info_text TEXT;
    v_has_biomarker BOOLEAN;
BEGIN
    -- Convert JSONB to TEXT for pattern matching
    v_design_info_text := p_design_info::TEXT;

    -- Determine if the study has biomarkers
    v_has_biomarker := has_biomarker_indicators(
        p_eligibility,
        p_outcomes,
        p_design_info,
        p_biospec_retention,
        p_biospec_description
    );

    -- Company size effect
    SELECT
        CASE p_company_size
            WHEN 'Early-stage Biotech' THEN 1.8
            WHEN 'Big Pharma' THEN 0.7
            WHEN 'Small Pharma' THEN 1.2
            ELSE 1.0
        END INTO v_company_multiplier;

    -- Calculate base market reaction score
    v_market_reaction := v_base_score * v_company_multiplier;

    -- Phase adjustment
    v_market_reaction := v_market_reaction * 
        CASE p_phase
            WHEN 'PHASE1' THEN 0.8
            WHEN 'PHASE2' THEN 1.0
            WHEN 'PHASE3' THEN 1.2
            WHEN 'FDA_REVIEW' THEN 1.3
            ELSE 0.7
        END;

    -- Biomarker bonus
    IF v_has_biomarker THEN
        v_market_reaction := v_market_reaction * 1.15;
    END IF;

    -- Design bonuses
    IF v_design_info_text IS NOT NULL THEN
        IF LOWER(v_design_info_text) LIKE '%double-blind%' OR LOWER(v_design_info_text) LIKE '%double blind%' THEN
            v_design_bonus := v_design_bonus + 0.1;
        END IF;

        IF LOWER(v_design_info_text) LIKE '%placebo%' THEN
            v_design_bonus := v_design_bonus + 0.1;
        END IF;

        IF LOWER(v_design_info_text) LIKE '%randomized%' OR LOWER(v_design_info_text) LIKE '%randomised%' THEN
            v_design_bonus := v_design_bonus + 0.1;
        END IF;

        -- Apply cumulative design bonus
        v_market_reaction := v_market_reaction * (1 + v_design_bonus);
    END IF;

    -- Keep score within 0-10 range
    RETURN GREATEST(0, LEAST(10, v_market_reaction));
END;
$$ LANGUAGE plpgsql;

-- Development Cost Calculation
CREATE OR REPLACE FUNCTION calculate_development_costs(
    p_phase VARCHAR,
    p_disease_area VARCHAR
) RETURNS DECIMAL AS $$
DECLARE
    v_base_cost DECIMAL;
    v_disease_multiplier DECIMAL;
BEGIN
    -- Base phase costs (in millions)
    SELECT
        CASE p_phase
            WHEN 'PHASE1' THEN 0.62
            WHEN 'PHASE2' THEN 30.48
            WHEN 'PHASE3' THEN 41.09
            WHEN 'FDA_REVIEW' THEN 638.75
            ELSE 58.51
        END INTO v_base_cost;

    -- Disease-specific multipliers
    SELECT
        CASE p_disease_area
            WHEN 'RESPIRATORY' THEN 2.13
            WHEN 'ONCOLOGY' THEN 1.45
            WHEN 'OPHTHALMOLOGY' THEN 1.28
            WHEN 'CARDIOVASCULAR' THEN 1.18
            WHEN 'ENDOCRINE' THEN 1.09
            WHEN 'INFECTIOUS_DISEASE' THEN 1.00
            WHEN 'CNS' THEN 0.98
            WHEN 'GENITOURINARY' THEN 0.81
            WHEN 'RARE_DISEASES' THEN 1.45
            WHEN 'AUTOIMMUNE' THEN 1.04
            WHEN 'METABOLIC' THEN 1.09
            WHEN 'VACCINES' THEN 1.00
            ELSE 1.00
        END INTO v_disease_multiplier;

    RETURN v_base_cost * v_disease_multiplier;
END;
$$ LANGUAGE plpgsql;

