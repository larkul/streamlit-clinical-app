-- Create consolidated clinical trials table
CREATE TABLE consolidated_clinical_trials (
    id SERIAL PRIMARY KEY,
    nct_id VARCHAR(20) UNIQUE NOT NULL,
    brief_title TEXT,
    official_title TEXT,
    sponsor_name VARCHAR(255),
    status VARCHAR(50),
    phase VARCHAR(50),
    study_type VARCHAR(100),
    enrollment INTEGER,
    start_date DATE,
    completion_date DATE,
    last_update_date DATE,
    conditions JSONB,
    outcome_measures JSONB,
    eligibility_criteria JSONB,
    biospec_retention TEXT,
    biospec_description TEXT,
    design_info JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_trials_nct_id ON consolidated_clinical_trials(nct_id);
CREATE INDEX idx_trials_sponsor ON consolidated_clinical_trials(sponsor_name);
CREATE INDEX idx_trials_phase ON consolidated_clinical_trials(phase);
CREATE INDEX idx_trials_status ON consolidated_clinical_trials(status);
CREATE INDEX idx_trials_completion_date ON consolidated_clinical_trials(completion_date);
