-- Core Tables
-- Disease areas table
CREATE TABLE disease_areas (
    id SERIAL PRIMARY KEY,
    area_name VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Disease area ranking table
CREATE TABLE disease_area_ranking (
    area_name VARCHAR PRIMARY KEY,
    rank INT
);

-- Hay probabilities table
CREATE TABLE hay_probabilities (
    id SERIAL PRIMARY KEY,
    disease_area_id INTEGER REFERENCES disease_areas(id),
    phase_1_to_2 DECIMAL(5,3),
    phase_2_to_3 DECIMAL(5,3),
    phase_3_to_nda_bla DECIMAL(5,3),
    nda_bla_to_approval DECIMAL(5,3),
    loa_from_current_phase DECIMAL(5,3),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Update logs table
CREATE TABLE update_logs (
    id SERIAL PRIMARY KEY,
    update_type VARCHAR(50),
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    status VARCHAR(20),
    records_processed INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Weekly summary stats table
CREATE TABLE weekly_summary_stats (
    id SERIAL PRIMARY KEY,
    report_date DATE,
    total_active_trials INTEGER,
    trials_by_phase JSONB,
    trials_by_disease JSONB,
    avg_market_values JSONB,
    high_value_opportunities JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Disease area alerts table
CREATE TABLE disease_area_alerts (
    id SERIAL PRIMARY KEY,
    alert_date DATE,
    disease_area VARCHAR(100),
    alert_type VARCHAR(50),
    alert_message TEXT,
    metric_value DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
