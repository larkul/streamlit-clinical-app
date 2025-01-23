CREATE OR REPLACE FUNCTION has_biomarker_indicators(
    p_eligibility JSONB,
    p_outcomes JSONB,
    p_design JSONB,
    p_biospec_retention TEXT,
    p_biospec_description TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_text_to_search TEXT;
    v_term TEXT[] := ARRAY[
        -- Original terms
        'genetic marker', 'DNA marker', 'RNA marker', 'protein marker', 
        'immune cell marker', 'T cell marker', 'B cell marker', 'stem cell marker', 
        'biomarker', 'biomarkers', 
        'genetic markers', 'DNA markers', 'RNA markers', 'protein markers', 
        'immune cell markers', 'T cell markers', 'B cell markers', 'stem cell markers',
        
        -- New terms without comma-separated entries
        'biological marker', 'biological markers', 
        'biologic marker', 'biologic markers', 
        'clinical marker', 'clinical markers', 
        'surrogate marker', 'surrogate markers', 
        'surrogate endpoint', 'surrogate endpoints', 
        'surrogate end point', 'surrogate end points', 
        'immune marker', 'immune markers', 
        'immunologic marker', 'immunologic markers', 
        'laboratory marker', 'laboratory markers', 
        'serum marker', 'serum markers', 
        'viral marker', 'viral markers', 
        'biochemical marker', 'biochemical markers'
    ];
    v_current_term TEXT;
BEGIN
    -- Combine all relevant fields into a single searchable string
    v_text_to_search := LOWER(
        COALESCE((p_eligibility->>'criteria')::TEXT, '') || ' ' ||
        COALESCE((p_outcomes->>'primary')::TEXT, '') || ' ' ||
        COALESCE((p_outcomes->>'secondary')::TEXT, '') || ' ' ||
        COALESCE((p_design->>'biomarker_description')::TEXT, '') || ' ' ||
        COALESCE(p_biospec_retention, '') || ' ' ||
        COALESCE(p_biospec_description, '')
    );

    -- Exit early if combined text is empty
    IF v_text_to_search IS NULL OR LENGTH(TRIM(v_text_to_search)) = 0 THEN
        RETURN FALSE;
    END IF;

    -- Loop through the hardcoded list of terms
    FOREACH v_current_term IN ARRAY v_term LOOP
        -- Check if the current term exists in the text as an exact phrase
        IF v_text_to_search ~* ('\m' || v_current_term || '\M') THEN
            RETURN TRUE; -- Match found
        END IF;
    END LOOP;

    RETURN FALSE; -- No matches found
END;
$$ LANGUAGE plpgsql;

