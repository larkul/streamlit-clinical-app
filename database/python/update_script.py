import requests
import json
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import Json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='ctmis_update.log'
)

def get_db_connection():
    """Create database connection using environment variables"""
    try:
        return psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT', '5432')
        )
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        raise

def process_trials(studies):
    """Process trial data from API response"""
    processed_trials = []
    
    for study in studies:
        try:
            protocol = study.get('protocolSection', {})
            
            # Extract module data
            identification = protocol.get('identificationModule', {})
            design_module = protocol.get('designModule', {})
            status_module = protocol.get('statusModule', {})
            sponsor_module = protocol.get('sponsorCollaboratorsModule', {})
            conditions_module = protocol.get('conditionsModule', {})
            outcomes_module = protocol.get('outcomesModule', {})
            eligibility_module = protocol.get('eligibilityModule', {})
            biospec_module = protocol.get('biospecModule', {})

            # Basic trial data
            trial_data = {
                'nct_id': identification.get('nctId'),
                'brief_title': identification.get('briefTitle'),
                'official_title': identification.get('officialTitle'),
                'sponsor_name': sponsor_module.get('leadSponsor', {}).get('name'),
                'status': status_module.get('overallStatus'),
                'phase': design_module.get('phases', [None])[0],
                'study_type': protocol.get('studyType'),
                'enrollment': status_module.get('enrollmentCount'),
                'start_date': status_module.get('startDate'),
                'completion_date': status_module.get('completionDate'),
                'last_update_date': status_module.get('lastUpdatePostDate'),
                
                # Complex fields as JSON
                'conditions': Json({
                    'conditions': conditions_module.get('conditions', []),
                    'keywords': conditions_module.get('keywords', [])
                }),
                
                'outcome_measures': Json({
                    'primary': outcomes_module.get('primaryOutcomes', []),
                    'secondary': outcomes_module.get('secondaryOutcomes', [])
                }),
                
                'eligibility_criteria': Json({
                    'criteria': eligibility_module.get('eligibilityCriteria'),
                    'gender': eligibility_module.get('gender'),
                    'min_age': eligibility_module.get('minimumAge'),
                    'max_age': eligibility_module.get('maximumAge'),
                    'healthy_volunteers': eligibility_module.get('healthyVolunteers')
                }),
                
                'biospec_retention': biospec_module.get('biospecRetention'),
                'biospec_description': biospec_module.get('biospecDescription'),
                
                'design_info': Json({
                    'allocation': design_module.get('designInfo', {}).get('allocation'),
                    'intervention_model': design_module.get('designInfo', {}).get('interventionModel'),
                    'primary_purpose': design_module.get('designInfo', {}).get('primaryPurpose'),
                    'masking': design_module.get('designInfo', {}).get('masking'),
                    'who_masked': design_module.get('designInfo', {}).get('maskingInfo', {}).get('whoMasked', [])
                })
            }

            # Validate required fields
            if not trial_data['nct_id']:
                logging.warning(f"Skipping trial without NCT ID")
                continue

            processed_trials.append(trial_data)
            
        except Exception as e:
            nct_id = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId', 'UNKNOWN')
            logging.error(f"Error processing trial {nct_id}: {e}")
            continue
    
    return processed_trials

def fetch_recent_updates(last_update_date):
    """Fetch trials updated since last update"""
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    next_token = None
    updated_trials = []
    
    if isinstance(last_update_date, datetime):
        last_update_date = last_update_date.strftime('%Y-%m-%d')
    
    params = {
        "query.term": f"(AREA[LeadSponsorClass] INDUSTRY) AND AREA[LastUpdatePostDate]RANGE[{last_update_date},MAX]",
        "pageSize": 1000,
        "fields": [
            "NCTId", "BriefTitle", "OfficialTitle", "Sponsor", 
            "Status", "Phase", "StudyType", "EnrollmentCount", 
            "StartDate", "CompletionDate", "LastUpdatePostDate",
            "Condition", "OutcomeMeasures", "EligibilityCriteria", 
            "BiospecRetention", "BiospecDescription", "DesignInfo"
        ]
    }

    while True:
        if next_token:
            params["pageToken"] = next_token

        try:
            logging.info(f"Fetching page with params: {params}")
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            studies = data.get("studies", [])
            
            if not studies:
                break
                
            logging.info(f"Processing {len(studies)} trials")
            processed = process_trials(studies)
            updated_trials.extend(processed)
            
            next_token = data.get("nextPageToken")
            if not next_token:
                break
                
        except requests.exceptions.RequestException as e:
            logging.error(f"API request error: {e}")
            break
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {e}")
            break
        except Exception as e:
            logging.error(f"Unexpected error in fetch_recent_updates: {e}")
            break

    return updated_trials

def update_database(conn, trials):
    """Update database with new trial data"""
    updated_count = 0
    inserted_count = 0
    
    with conn.cursor() as cur:
        for trial in trials:
            try:
                # Check if trial exists
                cur.execute(
                    "SELECT 1 FROM consolidated_clinical_trials WHERE nct_id = %s", 
                    (trial['nct_id'],)
                )
                exists = cur.fetchone() is not None

                # Upsert query
                query = """
                    INSERT INTO consolidated_clinical_trials (
                        nct_id, brief_title, official_title, sponsor_name,
                        status, phase, study_type, enrollment,
                        start_date, completion_date, last_update_date, 
                        conditions, outcome_measures, eligibility_criteria,
                        biospec_retention, biospec_description, design_info
                    ) VALUES (
                        %(nct_id)s, %(brief_title)s, %(official_title)s, %(sponsor_name)s,
                        %(status)s, %(phase)s, %(study_type)s, %(enrollment)s,
                        %(start_date)s, %(completion_date)s, %(last_update_date)s,
                        %(conditions)s, %(outcome_measures)s, %(eligibility_criteria)s,
                        %(biospec_retention)s, %(biospec_description)s, %(design_info)s
                    )
                    ON CONFLICT (nct_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        enrollment = EXCLUDED.enrollment,
                        completion_date = EXCLUDED.completion_date,
                        last_update_date = EXCLUDED.last_update_date,
                        conditions = EXCLUDED.conditions,
                        outcome_measures = EXCLUDED.outcome_measures,
                        eligibility_criteria = EXCLUDED.eligibility_criteria,
                        biospec_retention = EXCLUDED.biospec_retention,
                        biospec_description = EXCLUDED.biospec_description,
                        design_info = EXCLUDED.design_info,
                        updated_at = CURRENT_TIMESTAMP
                """
                
                cur.execute(query, trial)
                
                if exists:
                    updated_count += 1
                else:
                    inserted_count += 1
                
            except Exception as e:
                logging.error(f"Error updating trial {trial.get('nct_id')}: {e}")
                continue
        
        conn.commit()
        
    return updated_count, inserted_count

def main():
    """Main update process"""
    start_time = datetime.now()
    logging.info("Starting weekly update process")
    
    try:
        conn = get_db_connection()
        
        # Get last update date
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(last_update_date) FROM consolidated_clinical_trials")
            last_update = cur.fetchone()[0] or (datetime.now() - timedelta(days=7))
            logging.info(f"Last update date: {last_update}")
        
        # Fetch and process updates
        updated_trials = fetch_recent_updates(last_update)
        if updated_trials:
            updated_count, inserted_count = update_database(conn, updated_trials)
            
            # Update CTMIS calculations
            with conn.cursor() as cur:
                cur.execute("SELECT perform_weekly_update()")
                conn.commit()
            
            logging.info(f"Successfully processed {len(updated_trials)} trials")
            logging.info(f"Updated: {updated_count}, Inserted: {inserted_count}")
        else:
            logging.info("No updates found")
            
        end_time = datetime.now()
        duration = end_time - start_time
        logging.info(f"Update process completed in {duration}")
            
    except Exception as e:
        logging.error(f"Error during update process: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
