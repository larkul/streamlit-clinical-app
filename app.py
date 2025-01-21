import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import psycopg2

# Configure page
st.set_page_config(page_title="Clinical Trial Analysis Dashboard", layout="wide")

# Database connection
@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=st.secrets["postgresql"]["host"],
        port=st.secrets["postgresql"]["port"],
        database=st.secrets["postgresql"]["database"],
        user=st.secrets["postgresql"]["user"],
        password=st.secrets["postgresql"]["password"]
    )

def execute_query(conn, query, params=None):
    try:
        return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None

def main():
    st.title("Clinical Trials Analysis Dashboard")
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Initialize connection
    conn = init_connection()
    
    # Get unique disease areas for filter
    disease_areas = execute_query(conn, "SELECT DISTINCT area_name FROM disease_areas ORDER BY area_name")
    if disease_areas is not None:
        selected_diseases = st.sidebar.multiselect(
            "Select Disease Areas",
            options=disease_areas['area_name'].tolist(),
        )
    
    # Date range filter
    years = execute_query(conn, "SELECT DISTINCT EXTRACT(YEAR FROM completion_date)::int as year FROM consolidated_clinical_trials ORDER BY year DESC")
    if years is not None:
        min_year = years['year'].min()
        max_year = years['year'].max()
        selected_years = st.sidebar.slider(
            "Select Year Range",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year)
        )
    
    # Phase filter
    phases = st.sidebar.multiselect(
        "Select Phases",
        ["PHASE1", "PHASE2", "PHASE3", "FDA_REVIEW"]
    )
    
    # Build base query with filters
    base_query_conditions = []
    params = []
    
    if selected_diseases:
        base_query_conditions.append("disease_area = ANY(%s)")
        params.append(selected_diseases)
    
    if selected_years:
        base_query_conditions.append("EXTRACT(YEAR FROM completion_date) BETWEEN %s AND %s")
        params.extend(selected_years)
    
    if phases:
        base_query_conditions.append("phase = ANY(%s)")
        params.append(phases)
    
    where_clause = " AND ".join(base_query_conditions) if base_query_conditions else "1=1"
    
    # Get sponsor name from user
    sponsor_name = st.text_input("Enter Sponsor Name:")
    
    if sponsor_name:
        # Add sponsor filter to where clause
        where_clause = f"({where_clause}) AND LOWER(sponsor_name) LIKE LOWER(%s)"
        params.append(f"%{sponsor_name}%")
        
        # Get overall metrics
        metrics_query = f"""
        SELECT 
            COUNT(*) as total_trials,
            COUNT(CASE WHEN status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING') THEN 1 END) as active_trials,
            COUNT(DISTINCT disease_area) as unique_diseases,
            COUNT(DISTINCT phase) as unique_phases
        FROM consolidated_clinical_trials
        WHERE {where_clause}
        """
        
        metrics_df = execute_query(conn, metrics_query, params)
        
        if metrics_df is not None and not metrics_df.empty:
            # Display metrics in columns
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Trials", metrics_df['total_trials'].iloc[0])
            with col2:
                st.metric("Active Trials", metrics_df['active_trials'].iloc[0])
            with col3:
                st.metric("Disease Areas", metrics_df['unique_diseases'].iloc[0])
            with col4:
                st.metric("Trial Phases", metrics_df['unique_phases'].iloc[0])
        
        # Get trials by disease area and status
        disease_query = f"""
        SELECT 
            disease_area,
            status,
            COUNT(*) as trial_count
        FROM consolidated_clinical_trials
        WHERE {where_clause}
        GROUP BY disease_area, status
        ORDER BY disease_area, status
        """
        
        disease_df = execute_query(conn, disease_query, params)
        
        if disease_df is not None and not disease_df.empty:
            # Create stacked bar chart
            fig_disease = px.bar(
                disease_df,
                x='disease_area',
                y='trial_count',
                color='status',
                title='Trials by Disease Area and Status',
                labels={'disease_area': 'Disease Area', 'trial_count': 'Number of Trials'}
            )
            st.plotly_chart(fig_disease, use_container_width=True)
        
        # Get trials by phase
        phase_query = f"""
        SELECT 
            phase,
            COUNT(*) as trial_count
        FROM consolidated_clinical_trials
        WHERE {where_clause}
        GROUP BY phase
        ORDER BY phase
        """
        
        phase_df = execute_query(conn, phase_query, params)
        
        if phase_df is not None and not phase_df.empty:
            fig_phase = px.bar(
                phase_df,
                x='phase',
                y='trial_count',
                title='Trials by Phase',
                labels={'phase': 'Phase', 'trial_count': 'Number of Trials'}
            )
            st.plotly_chart(fig_phase, use_container_width=True)
        
        # Create tabs for detailed analysis
        tab1, tab2, tab3 = st.tabs(["Completed Trials", "Active Trials Analysis", "Market Analysis"])
        
        with tab1:
            completed_query = f"""
            SELECT 
                nct_id,
                brief_title,
                phase,
                disease_area,
                completion_date
            FROM consolidated_clinical_trials
            WHERE {where_clause} AND status = 'COMPLETED'
            ORDER BY completion_date DESC
            """
            
            completed_df = execute_query(conn, completed_query, params)
            if completed_df is not None:
                st.dataframe(completed_df)
        
        with tab2:
            active_query = f"""
            SELECT 
                nct_id,
                brief_title,
                phase,
                disease_area,
                phase_success_probability,
                likelihood_of_approval
            FROM streamlit_ctmis_view
            WHERE {where_clause} AND status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING')
            """
            
            active_df = execute_query(conn, active_query, params)
            if active_df is not None:
                # Success probability by phase
                fig_success = px.scatter(
                    active_df,
                    x='phase',
                    y='phase_success_probability',
                    color='disease_area',
                    title='Success Probability by Phase',
                    labels={'phase_success_probability': 'Success Probability'}
                )
                st.plotly_chart(fig_success, use_container_width=True)
        
        with tab3:
            market_query = f"""
            SELECT 
                nct_id,
                brief_title,
                phase,
                disease_area,
                ctmis_score,
                estimated_market_value/1000000 as value_millions,
                expected_return/1000000 as return_millions
            FROM streamlit_ctmis_view
            WHERE {where_clause}
            """
            
            market_df = execute_query(conn, market_query, params)
            if market_df is not None:
                # Market value analysis
                fig_market = px.scatter(
                    market_df,
                    x='value_millions',
                    y='ctmis_score',
                    color='phase',
                    size='return_millions',
                    hover_data=['brief_title'],
                    title='Market Value vs CTMIS Score',
                    labels={
                        'value_millions': 'Estimated Market Value (Millions)',
                        'ctmis_score': 'CTMIS Score',
                        'return_millions': 'Expected Return (Millions)'
                    }
                )
                st.plotly_chart(fig_market, use_container_width=True)

if __name__ == "__main__":
    main()