-- Create biomarker categories table
CREATE TABLE biomarker_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create biomarker terms table
CREATE TABLE biomarker_terms (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES biomarker_categories(id),
    term VARCHAR(255) NOT NULL,
    search_terms TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert biomarker categories
INSERT INTO biomarker_categories (category_name, description) VALUES 
('MOLECULAR', 'Molecular and genetic biomarkers'),
('CELLULAR', 'Cell-based biomarkers'),
('IMAGING', 'Imaging biomarkers'),
('PHYSIOLOGICAL', 'Physiological measurements'),
('PROGNOSTIC', 'Disease progression markers'),
('PREDICTIVE', 'Treatment response markers'),
('DIAGNOSTIC', 'Disease identification markers'),
('SAFETY', 'Safety and toxicity markers');

-- Insert comprehensive biomarker terms
INSERT INTO biomarker_terms (category_id, term, search_terms) VALUES
-- Molecular biomarkers
(1, 'genetic marker', ARRAY['genetic marker', 'genetic markers', 'gene marker', 'genetic biomarker', 'genomic marker']),
(1, 'DNA marker', ARRAY['DNA marker', 'DNA markers', 'DNA biomarker', 'genetic marker']),
(1, 'RNA marker', ARRAY['RNA marker', 'RNA markers', 'RNA biomarker', 'expression marker']),
(1, 'protein marker', ARRAY['protein marker', 'protein markers', 'protein biomarker', 'proteomic marker']),
(1, 'metabolite marker', ARRAY['metabolite marker', 'metabolite markers', 'metabolic marker', 'metabolomic marker']),
-- Cellular biomarkers
(2, 'cell surface marker', ARRAY['cell surface marker', 'surface marker', 'cellular marker']),
(2, 'immune cell marker', ARRAY['immune cell marker', 'immune marker', 'immunological marker']),
(2, 'T cell marker', ARRAY['T cell marker', 'T-cell marker', 'T lymphocyte marker']),
(2, 'B cell marker', ARRAY['B cell marker', 'B-cell marker', 'B lymphocyte marker']),
(2, 'stem cell marker', ARRAY['stem cell marker', 'progenitor marker', 'stemness marker']),
-- Imaging biomarkers
(3, 'imaging biomarker', ARRAY['imaging biomarker', 'imaging marker', 'radiological marker']),
(3, 'MRI marker', ARRAY['MRI marker', 'magnetic resonance marker', 'imaging marker']),
(3, 'PET marker', ARRAY['PET marker', 'positron emission marker', 'nuclear imaging marker']),
(3, 'CT marker', ARRAY['CT marker', 'computed tomography marker', 'radiological marker']);

-- Function to identify biomarker indicators in trial data
CREATE OR REPLACE FUNCTION has_biomarker_indicators(
    p_eligibility JSONB,
    p_outcomes JSONB,
    p_design JSONB,
    p_biospec_retention TEXT,
    p_biospec_description TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_text_to_search TEXT;
    v_term RECORD;
    v_category RECORD;
BEGIN
    -- Combine relevant text fields
    v_text_to_search := COALESCE(p_eligibility::TEXT, '') || ' ' ||
                       COALESCE(p_outcomes::TEXT, '') || ' ' ||
                       COALESCE(p_design::TEXT, '') || ' ' ||
                       COALESCE(p_biospec_retention, '') || ' ' ||
                       COALESCE(p_biospec_description, '');
    
    -- Check biospec retention first
    IF p_biospec_retention IS NOT NULL THEN
        RETURN TRUE;
    END IF;
    
    -- Search for category and term matches
    FOR v_category IN SELECT * FROM biomarker_categories LOOP
        IF v_text_to_search ILIKE '%' || v_category.category_name || '%' THEN
            RETURN TRUE;
        END IF;
        
        FOR v_term IN 
            SELECT * FROM biomarker_terms 
            WHERE category_id = v_category.id 
        LOOP
            -- Check each search term
            IF EXISTS (
                SELECT 1
                FROM unnest(v_term.search_terms) t
                WHERE v_text_to_search ILIKE '%' || t || '%'
            ) THEN
                RETURN TRUE;
            END IF;
        END LOOP;
    END LOOP;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;
