# Clinical Trial Analysis Platform

## Overview
This platform analyzes clinical trial data using Streamlit and PostgreSQL, providing insights into trial success probabilities, market value estimations, and biomarker analysis.

## Structure

```
├── app.py                    # Streamlit application
├── database/                 # Database components
│   ├── init/                # Database initialization
│   │   ├── 01_extensions.sql
│   │   ├── 02_tables.sql
│   │   ├── 03_disease_data.sql
│   │   ├── 04_indexes.sql
│   │   └── 05_biomarkers.sql
│   ├── functions/           # Database functions
│   ├── views/              # Database views
│   ├── updates/            # Update scripts
│   └── python/             # Python utilities
└── requirements.txt         # Python dependencies
```

## Features
- Clinical trial success probability calculations
- Market value and return estimations
- Disease area analysis
- Biomarker detection
- Weekly data updates from ClinicalTrials.gov

## Setup

1. Database Setup
```sql
cd database
psql -h your-host -U your-user -d your-database -f init.sql
```

2. Python Environment
```bash
pip install -r requirements.txt
```

3. Environment Variables
Create `.env` file with:
```
DB_NAME=postgres
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=your_host
DB_PORT=5432
```

4. Run Application
```bash
streamlit run app.py
```

## Data Updates
Weekly updates fetch new trial data through:
```bash
python database/python/update_script.py
```

## Analysis Components
- Trial success probability based on disease area and phase
- Market value calculations using industry benchmarks
- Biomarker analysis across molecular, cellular, and imaging categories
- Portfolio analysis for sponsors

## Contributing
1. Fork repository
2. Create feature branch
3. Commit changes
4. Submit pull request

## Contact
For questions or issues, please open an issue in the repository.
