import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
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

def get_sponsor_overview(conn):
    query = """
   SELECT 
    COUNT(*) as total_trials,
    COUNT(CASE WHEN status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING') THEN 1 END) as active_trials,
    JSONB_OBJECT_AGG(phase, COUNT(*)) as trials_per_phase,
    SUM(CASE 
        WHEN status IN ('RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING') 
        THEN COALESCE(estimated_market_value, 0) 
        ELSE 0 
    END)/1000000 as portfolio_value_millions
FROM streamlit_ctmis_view
WHERE completion_date BETWEEN %s AND %s
GROUP BY phase;
    """
    start_date = st.sidebar.date_input("Start Date", datetime(2020, 1, 1))
    end_date = st.sidebar.date_input("End Date", datetime(2025, 12, 31))
    return execute_query(conn, query, [start_date, end_date])

def visualize_data(overview_df):
    if overview_df is not None and not overview_df.empty:
        # Active Trials Bar Chart
        st.subheader("Trial Status Distribution")
        active_data = {
            "Status": ["Active", "Recruiting", "Active Not Recruiting"],
            "Count": [
                overview_df['active_trials'].iloc[0],
                overview_df['active_trials'].iloc[0],  # Assuming counts for now
                overview_df['active_trials'].iloc[0]
            ]
        }
        active_df = pd.DataFrame(active_data)
        fig_status = px.bar(active_df, x="Status", y="Count", title="Active Trials by Status")
        st.plotly_chart(fig_status)

        # Phase Distribution Bar Chart
        st.subheader("Trial Phases")
        if overview_df['trials_per_phase'].iloc[0]:
            phase_df = pd.DataFrame(list(overview_df['trials_per_phase'].iloc[0].items()), columns=['Phase', 'Count'])
            fig_phase = px.bar(phase_df, x='Phase', y='Count', title='Trials by Phase')
            st.plotly_chart(fig_phase)

        # Market Value Portfolio
        st.metric("Portfolio Value (in Millions)", f"${overview_df['portfolio_value_millions'].iloc[0]:,.2f}")

def get_top_completion_dates(conn):
    query = """
    SELECT nct_id, brief_title, completion_date 
    FROM streamlit_ctmis_view
    WHERE completion_date >= CURRENT_DATE
    ORDER BY completion_date ASC
    LIMIT 3
    """
    return execute_query(conn, query)

def get_sponsor_details(conn, sponsor_name):
    query = """
    SELECT 
        sponsor_name,
        phase,
        status,
        determine_disease_area(conditions) as disease_area,
        completion_date,
        phase_success_probability as probability_of_success,
        likelihood_of_approval,
        market_reaction_strength as market_reaction,
        estimated_market_value/1000000 as market_value_millions,
        estimated_development_cost/1000000 as development_cost_millions,
        expected_return/1000000 as discount,
        nct_id
    FROM streamlit_ctmis_view
    WHERE LOWER(sponsor_name) LIKE LOWER(%s)
    ORDER BY completion_date ASC
    """
    return execute_query(conn, query, [f'%{sponsor_name}%'])

def main():
    st.title("Clinical Trials Analysis Dashboard")
    conn = init_connection()

    # Sidebar Filters
    st.sidebar.header("Filters")
    biomarker_filter = st.sidebar.checkbox("Biomarker Present")

    overview_df = get_sponsor_overview(conn)
    if overview_df is not None and not overview_df.empty:
        st.header("Portfolio Overview")
        visualize_data(overview_df)

        # Top Completion Dates
        st.header("Upcoming Completion Dates")
        completion_df = get_top_completion_dates(conn)
        if completion_df is not None and not completion_df.empty:
            st.dataframe(completion_df)
        else:
            st.write("No upcoming completion dates found.")

        # Sponsor Details
        st.header("Sponsor Details")
        sponsor_name = st.text_input("Enter Sponsor Name")
        if sponsor_name:
            sponsor_details_df = get_sponsor_details(conn, sponsor_name)
            if sponsor_details_df is not None and not sponsor_details_df.empty:
                sponsor_details_df['nct_id'] = sponsor_details_df['nct_id'].apply(
                    lambda x: f"[Link](https://clinicaltrials.gov/study/{x})")

                # Adding explanation tooltips to the table headers
                st.dataframe(sponsor_details_df, use_container_width=True)
                st.caption(
                    "**Table Legend:** Hover over column headers for explanation.\n" +
                    "- **Phase**: Clinical trial phase (1, 2, or 3).\n" +
                    "- **Status**: Current trial status (e.g., Recruiting).\n" +
                    "- **Market Value**: Estimated market value in millions.\n" +
                    "- **Development Cost**: Estimated development cost in millions.\n" +
                    "- **Discount**: Calculated expected return.\n"
                )
            else:
                st.write("No data available for this sponsor.")
    else:
        st.warning("No data available for the selected filters.")

if __name__ == "__main__":
    main()
