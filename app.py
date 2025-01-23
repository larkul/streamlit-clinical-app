import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

# Page configuration
st.set_page_config(
    page_title="Clinical Trial Analysis Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection
@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=st.secrets["postgresql"]["host"],
        port=st.secrets["postgresql"]["port"],
        database=st.secrets["postgresql"]["database"],
        user=st.secrets["postgresql"]["user"],
        password=st.secrets["postgresql"]["password"],
        cursor_factory=RealDictCursor
    )

def execute_query(conn, query, params=None):
    try:
        return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None

def get_sponsor_overview(conn, sponsor_name):
    query = """
    SELECT 
        COUNT(*) as total_trials,
        COUNT(CASE WHEN status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING') THEN 1 END) as active_trials,
        COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_trials,
        ARRAY_AGG(DISTINCT EXTRACT(YEAR FROM completion_date)) as trial_years,
        JSONB_OBJECT_AGG(phase, COUNT(*)) FILTER (WHERE phase IS NOT NULL) as trials_per_phase,
        SUM(CASE 
            WHEN status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING') 
            THEN COALESCE(estimated_market_value, 0) 
            ELSE 0 
        END)/1000000 as portfolio_value_millions
    FROM consolidated_clinical_trials
    WHERE LOWER(sponsor_name) LIKE LOWER(%s)
    GROUP BY sponsor_name
    """
    return execute_query(conn, query, [f'%{sponsor_name}%'])

def create_sponsor_visualizations(conn, sponsor_name):
    query = """
    SELECT 
        phase,
        status,
        EXTRACT(YEAR FROM completion_date) as year,
        determine_disease_area(conditions) as disease_area,
        estimated_market_value/1000000 as value_millions,
        has_biomarker_indicators(
            eligibility_criteria,
            outcome_measures,
            design_info,
            biospec_retention,
            biospec_description
        ) as has_biomarker
    FROM consolidated_clinical_trials
    WHERE LOWER(sponsor_name) LIKE LOWER(%s)
    """
    df = execute_query(conn, query, [f'%{sponsor_name}%'])
    
    if df is not None and not df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Phase Distribution
            phase_df = df['phase'].value_counts().reset_index()
            phase_df.columns = ['Phase', 'Count']
            fig_phase = px.pie(phase_df, 
                             values='Count',
                             names='Phase',
                             title='Trials by Phase')
            st.plotly_chart(fig_phase, use_container_width=True)
            
            # Status Distribution
            status_df = df['status'].value_counts().reset_index()
            status_df.columns = ['Status', 'Count']
            fig_status = px.bar(status_df,
                              x='Status',
                              y='Count',
                              title='Trial Status Distribution')
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            # Trials by Year
            yearly_trials = df.groupby('year').size().reset_index(name='count')
            fig_yearly = px.line(yearly_trials,
                               x='year',
                               y='count',
                               title='Trials by Year',
                               markers=True)
            st.plotly_chart(fig_yearly, use_container_width=True)
            
            # Disease Area Distribution
            disease_df = df['disease_area'].value_counts().reset_index()
            disease_df.columns = ['Disease Area', 'Count']
            fig_disease = px.bar(disease_df,
                               x='Disease Area',
                               y='Count',
                               title='Trials by Disease Area')
            fig_disease.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig_disease, use_container_width=True)

def get_trial_details(conn, sponsor_name, status_filter=None, phase_filter=None):
    query = """
    SELECT 
        nct_id,
        brief_title,
        phase,
        status,
        determine_disease_area(conditions) as disease_area,
        completion_date,
        CASE 
            WHEN status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING') THEN
                phase_success_probability
            ELSE NULL
        END as success_probability,
        CASE 
            WHEN status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING') THEN
                likelihood_of_approval
            ELSE NULL
        END as likelihood_of_approval,
        CASE 
            WHEN status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING') THEN
                market_reaction_strength
            ELSE NULL
        END as market_reaction,
        estimated_market_value/1000000 as market_value_millions,
        estimated_development_cost/1000000 as development_cost_millions,
        expected_return/1000000 as expected_return_millions,
        has_biomarker_indicators(
            eligibility_criteria,
            outcome_measures,
            design_info,
            biospec_retention,
            biospec_description
        ) as has_biomarker
    FROM streamlit_ctmis_view
    WHERE LOWER(sponsor_name) LIKE LOWER(%s)
    """
    params = [f'%{sponsor_name}%']
    
    if status_filter:
        query += " AND status = ANY(%s)"
        params.append(status_filter)
    if phase_filter:
        query += " AND phase = ANY(%s)"
        params.append(phase_filter)
        
    query += " ORDER BY completion_date DESC"
    
    return execute_query(conn, query, params)

def main():
    st.title("Clinical Trials Analysis Dashboard")
    
    conn = init_connection()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range filter
    st.sidebar.subheader("Date Range")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("From", value=datetime(2020, 1, 1))
    with col2:
        end_date = st.date_input("To", value=datetime(2025, 12, 31))

    # Status filter
    statuses = st.sidebar.multiselect(
        "Status",
        ["RECRUITING", "ACTIVE", "ACTIVE_NOT_RECRUITING", "COMPLETED"]
    )

    # Phase filter
    phases = st.sidebar.multiselect(
        "Phases",
        ["PHASE1", "PHASE2", "PHASE3"]
    )

    # Sponsor search
    sponsor_name = st.text_input("Enter Sponsor Name:")
    
    if sponsor_name:
        # Get sponsor overview
        overview_df = get_sponsor_overview(conn, sponsor_name)
        
        if overview_df is not None and not overview_df.empty:
            st.header("Portfolio Overview")
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Trials", overview_df['total_trials'].iloc[0])
                st.metric("Active Trials", overview_df['active_trials'].iloc[0])
            with col2:
                st.metric("Completed Trials", overview_df['completed_trials'].iloc[0])
                if overview_df['portfolio_value_millions'].iloc[0]:
                    st.metric("Portfolio Value", 
                             f"${overview_df['portfolio_value_millions'].iloc[0]:,.1f}M")
            with col3:
                st.write("Trials by Phase")
                if overview_df['trials_per_phase'].iloc[0]:
                    st.json(overview_df['trials_per_phase'].iloc[0])
            
            # Create visualizations
            st.header("Portfolio Analysis")
            create_sponsor_visualizations(conn, sponsor_name)
            
            # Get trial details
            st.header("Trial Details")
            trials_df = get_trial_details(conn, sponsor_name, statuses, phases)
            
            if trials_df is not None and not trials_df.empty:
                # Format display dataframe
                display_df = trials_df.copy()
                display_df['completion_date'] = pd.to_datetime(display_df['completion_date']).dt.strftime('%Y-%m-%d')
                display_df['success_probability'] = display_df['success_probability'].apply(
                    lambda x: f"{x:.1%}" if pd.notnull(x) else "N/A")
                display_df['likelihood_of_approval'] = display_df['likelihood_of_approval'].apply(
                    lambda x: f"{x:.1%}" if pd.notnull(x) else "N/A")
                display_df['market_value_millions'] = display_df['market_value_millions'].apply(
                    lambda x: f"${x:,.1f}M" if pd.notnull(x) else "N/A")
                display_df['development_cost_millions'] = display_df['development_cost_millions'].apply(
                    lambda x: f"${x:,.1f}M" if pd.notnull(x) else "N/A")
                display_df['expected_return_millions'] = display_df['expected_return_millions'].apply(
                    lambda x: f"${x:,.1f}M" if pd.notnull(x) else "N/A")
                
                st.dataframe(display_df)
                
                # Download button
                csv = trials_df.to_csv(index=False)
                st.download_button(
                    label="Download Data as CSV",
                    data=csv,
                    file_name=f"{sponsor_name}_trials.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No trials found matching the selected criteria.")
        else:
            st.warning("No data found for this sponsor.")

if __name__ == "__main__":
    main()
