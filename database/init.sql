-- Main initialization script
-- Run this to set up the entire database structure

-- First, run extensions
\i init/01_extensions.sql

-- Create base tables
\i init/02_tables.sql

-- Load initial disease data
\i init/03_disease_data.sql

-- Create indexes
\i init/04_indexes.sql

-- Create functions
\i functions/disease_functions.sql
\i functions/probability_functions.sql
\i functions/market_functions.sql
\i functions/utility_functions.sql

-- Create views
\i views/streamlit_view.sql
\i views/analysis_views.sql

-- Set up updates
\i updates/weekly_update.sql

-- Initialize the view
SELECT update_streamlit_view();
