-- Index on the phase column in consolidated_clinical_trials for quick filtering
CREATE INDEX IF NOT EXISTS idx_ct_phase ON consolidated_clinical_trials(phase);

-- Index on the status column in consolidated_clinical_trials for filtering
CREATE INDEX IF NOT EXISTS idx_ct_status ON consolidated_clinical_trials(status);

-- Index on the disease area for faster joins
CREATE INDEX IF NOT EXISTS idx_da_area_name ON disease_areas(area_name);

-- Index on hay_probabilities for faster joins
CREATE INDEX IF NOT EXISTS idx_hp_disease_area_id ON hay_probabilities(disease_area_id);

