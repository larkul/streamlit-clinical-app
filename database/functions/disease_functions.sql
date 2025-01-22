-- Drop the old function if it exists
DROP FUNCTION IF EXISTS determine_disease_area(TEXT);

-- Create the updated function to avoid duplicate disease assignments
CREATE OR REPLACE FUNCTION determine_disease_area(p_conditions TEXT)
RETURNS VARCHAR AS $$
BEGIN
    RETURN (
        SELECT da.area_name
        FROM disease_areas da
        JOIN disease_area_ranking dar ON da.area_name = dar.area_name  -- Dynamic ranking
        WHERE p_conditions ILIKE '%' || da.area_name || '%'
        ORDER BY dar.rank  -- Uses ranking table for prioritization
        LIMIT 1  -- Ensures only one disease area is assigned
    );
END;
$$ LANGUAGE plpgsql;

-- Create a function to get disease area details
CREATE OR REPLACE FUNCTION get_disease_area_details(p_area_name VARCHAR)
RETURNS TABLE (
    area_name VARCHAR,
    description TEXT,
    rank INT,
    trial_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        da.area_name,
        da.description,
        dar.rank,
        COUNT(DISTINCT ct.nct_id) as trial_count
    FROM disease_areas da
    LEFT JOIN disease_area_ranking dar ON da.area_name = dar.area_name
    LEFT JOIN consolidated_clinical_trials ct ON determine_disease_area(ct.conditions) = da.area_name
    WHERE da.area_name = p_area_name
    GROUP BY da.area_name, da.description, dar.rank;
END;
$$ LANGUAGE plpgsql;
