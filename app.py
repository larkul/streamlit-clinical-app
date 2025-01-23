import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure page
st.set_page_config(page_title="Clinical Trial Analysis Dashboard", layout="wide")

# Database connection
@st.cache_resource
def init_connection():
    try:
        return psycopg2.connect(
            host=st.secrets["postgresql"]["host"],
            port=st.secrets["postgresql"]["port"],
            database=st.secrets["postgresql"]["database"],
            user=st.secrets["postgresql"]["user"],
            password=st.secrets["postgresql"]["password"],
            cursor_factory=RealDictCursor
        )
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

def execute_query(conn, query, params=None):
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            results = cur.fetchall()
            return pd.DataFrame(results, columns=columns)
    except Exception as e:
        st.error(f"Query execution error: {e}")
        return None

def get_sponsor_suggestions(conn):
    query = """
    SELECT DISTINCT sponsor_name 
    FROM consolidated_clinical_trials 
    WHERE sponsor_name IS NOT NULL
    ORDER BY sponsor_name
    """
    return execute_query(conn, query)

def create_overview_charts(trials_df):
    col1, col2 = st.columns(2)
    
    with col1:
        # Trials by Phase
        phase_counts = trials_df['phase'].value_counts().reset_index()
        phase_counts.columns = ['Phase', 'Count']
        fig_phase = px.bar(phase_counts, x='Phase', y='Count', 
                          title='Trials by Phase',
                          color='Phase')
        st.plotly_chart(fig_phase, use_container_width=True)
        
        # Trials by Status
        status_counts = trials_df['status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        fig_status = px.pie(status_counts, values='Count', names='Status', 
                           title='Trial Status Distribution')
        st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        # Trials by Disease Area
        if 'disease_area' in trials_df.columns:
            disease_counts = trials_df['disease_area'].value_counts().head(10).reset_index()
            disease_counts.columns = ['Disease Area', 'Count']
            fig_disease = px.bar(disease_counts, x='Disease Area', y='Count',
                                title='Top 10 Disease Areas',
                                color='Disease Area')
            fig_disease.update_layout(showlegend=False)
            fig_disease.update_xaxes(tickangle=45)
            st.plotly_chart(fig_disease, use_container_width=True)
        
        # Trials by Year
        trials_df['year'] = pd.to_datetime(trials_df['completion_date']).dt.year
        year_counts = trials_df['year'].value_counts().sort_index().reset_index()
        year_counts.columns = ['Year', 'Count']
        fig_year = px.line(year_counts, x='Year', y='Count',
                          title='Trials by Year',
                          markers=True)
        st.plotly_chart(fig_year, use_container_width=True)

def main():
    st.title("Clinical Trials Analysis Dashboard")
    
    # Initialize connection
    conn = init_connection()
    if conn is None:
        st.error("Failed to connect to database")
        return

    # Sidebar filters
    st.sidebar.header("Filters")

    # Date range filter
    st.sidebar.subheader("Date Range")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("From", value=datetime(2020, 1, 1))
    with col2:
        end_date = st.date_input("To", value=datetime(2025, 12, 31))

    # Get unique disease areas
    disease_query = """
    SELECT DISTINCT area_name 
    FROM disease_areas 
    WHERE area_name IS NOT NULL 
    ORDER BY area_name
    """
    diseases_df = execute_query(conn, disease_query)
    if diseases_df is not None:
        selected_diseases = st.sidebar.multiselect(
            "Disease Areas",
            options=diseases_df['area_name'].tolist()
        )

    # Phase filter
    phases = st.sidebar.multiselect(
        "Phases",
        ["PHASE1", "PHASE2", "PHASE3"]
    )

    # Status filter
    statuses = st.sidebar.multiselect(
        "Status",
        ["RECRUITING", "ACTIVE", "ACTIVE_NOT_RECRUITING", "COMPLETED"]
    )

    # Market reaction strength filter
    market_reactions = st.sidebar.multiselect(
        "Market Reaction Strength",
        ["Strong", "Moderate", "Weak"]
    )

    # Multi-sponsor selection
    sponsors_df = get_sponsor_suggestions(conn)
    if sponsors_df is not None:
        selected_sponsors = st.multiselect(
            "Select sponsors",
            options=sponsors_df['sponsor_name'].tolist()
        )

        if selected_sponsors:
            # Build query conditions
            conditions = ["sponsor_name = ANY(%s)"]
            params = [selected_sponsors]

            if start_date and end_date:
                conditions.append("completion_date BETWEEN %s AND %s")
                params.extend([start_date, end_date])

            if selected_diseases:
                conditions.append("da.area_name = ANY(%s)")
                params.append(selected_diseases)

            if phases:
                conditions.append("phase = ANY(%s)")
                params.append(phases)

            if statuses:
                conditions.append("status = ANY(%s)")
                params.append(statuses)

            # Base query for all trials
            base_query = f"""
            SELECT 
                ct.sponsor_name,
                ct.nct_id,
                ct.brief_title,
                da.area_name as disease_area,
                ct.phase,
                ct.status,
                ct.completion_date
            FROM consolidated_clinical_trials ct
            LEFT JOIN disease_areas da ON determine_disease_area(ct.conditions) = da.area_name
            WHERE {" AND ".join(conditions)}
            """

            # Query for active trials with calculations
            active_query = f"""
            SELECT 
                cv.sponsor_name,
                cv.nct_id,
                cv.brief_title,
                cv.disease_area,
                cv.phase,
                cv.status,
                cv.completion_date,
                cv.phase_success_probability,
                cv.likelihood_of_approval,
                cv.market_reaction_strength
            FROM streamlit_ctmis_view cv
            WHERE cv.sponsor_name = ANY(%s)
            AND cv.status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING')
            AND cv.phase IN ('PHASE1', 'PHASE2', 'PHASE3')
            """

            # Execute queries
            base_trials_df = execute_query(conn, base_query, params)
            active_trials_df = execute_query(conn, active_query, [selected_sponsors])

            if base_trials_df is not None:
                # Create overview section
                st.header("Portfolio Overview")
                create_overview_charts(base_trials_df)
                
                # Display trials table
                st.header("Trial Details")
                
                if active_trials_df is not None:
                    # Format active trials
                    active_display_df = active_trials_df.copy()
                    active_display_df['completion_date'] = pd.to_datetime(active_display_df['completion_date']).dt.strftime('%Y-%m-%d')
                    active_display_df['phase_success_probability'] = active_display_df['phase_success_probability'].apply(
                        lambda x: f"{x:.1%}" if pd.notnull(x) else "N/A")
                    active_display_df['likelihood_of_approval'] = active_display_df['likelihood_of_approval'].apply(
                        lambda x: f"{x:.1%}" if pd.notnull(x) else "N/A")
                    
                    # Get completed trials
                    completed_mask = base_trials_df['status'] == 'COMPLETED'
                    completed_display_df = base_trials_df[completed_mask].copy()
                    completed_display_df['completion_date'] = pd.to_datetime(completed_display_df['completion_date']).dt.strftime('%Y-%m-%d')
                    completed_display_df['phase_success_probability'] = 'Completed trial'
                    completed_display_df['likelihood_of_approval'] = 'Completed trial'
                    completed_display_df['market_reaction_strength'] = 'Completed trial'
                    
                    # Combine and display
                    display_df = pd.concat([active_display_df, completed_display_df])
                    
                    st.dataframe(
                        display_df,
                        hide_index=True,
                        column_config={
                            "sponsor_name": "Sponsor",
                            "nct_id": "NCT ID",
                            "brief_title": "Trial Title",
                            "disease_area": "Disease Area",
                            "phase": "Phase",
                            "status": "Status",
                            "completion_date": "Completion Date",
                            "phase_success_probability": "Phase Success Probability",
                            "likelihood_of_approval": "Likelihood of Approval",
                            "market_reaction_strength": "Market Reaction"
                        }
                    )

                    # Add download button
                    csv = display_df.to_csv(index=False)
                    st.download_button(
                        label="Download Data as CSV",
                        data=csv,
                        file_name="clinical_trials.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No active trials found matching the selected criteria.")
            else:
                st.warning("No trials found matching the selected criteria.")

if __name__ == "__main__":
    main()
