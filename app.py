import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

# Configure page
st.set_page_config(page_title="Clinical Trial Outcome Prediction", layout="wide")

# Database connection using st.secrets
@st.cache_resource
def init_connection():
    """
    Establish a new database connection.
    """
    try:
        return psycopg2.connect(
            host=st.secrets["postgresql"]["host"],
            port=st.secrets["postgresql"]["port"],
            database=st.secrets["postgresql"]["database"],
            user=st.secrets["postgresql"]["user"],
            password=st.secrets["postgresql"]["password"]
        )
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return None

def ensure_connection(conn):
    """
    Ensure the connection is open. If closed, re-establish it.
    """
    if conn.closed != 0:  # Connection is closed if `closed` is non-zero
        conn = init_connection()
    return conn

def execute_query(conn, query, params=None):
    """
    Execute a SQL query and return the result as a Pandas DataFrame.
    """
    try:
        conn = ensure_connection(conn)
        return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None

def search_sponsor(conn, sponsor_name):
    query = """
    SELECT nct_id, brief_title, phase, status, disease_area, completion_date, 
           phase_success_probability, value_millions, ctmis_score, return_millions
    FROM search_sponsor(%s)
    """
    return execute_query(conn, query, params=[sponsor_name])

def get_sponsor_summary(conn, sponsor_name):
    query = """
    SELECT total_trials, active_trials, unique_diseases, biomarker_trial_count, 
           avg_success_probability, avg_market_reaction, 
           portfolio_value_millions, portfolio_cost_millions, portfolio_return_millions
    FROM get_sponsor_summary(%s)
    """
    return execute_query(conn, query, params=[sponsor_name])

def main():
    st.title("Clinical Trials Sponsor Analysis")
    
    # Sidebar for filters and information
    st.sidebar.header("About")
    st.sidebar.info("""
    This application allows you to analyze clinical trial sponsors and their 
    probability of success, market reactions, and portfolio analysis.
    """)

    # Main search interface
    sponsor_name = st.text_input("Enter Sponsor Name to Search:")
    
    if sponsor_name:
        conn = init_connection()  # Cached connection
        if conn:
            # Get sponsor summary
            summary_df = get_sponsor_summary(conn, sponsor_name)
            if summary_df is not None and not summary_df.empty:
                st.subheader("Sponsor Portfolio Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Trials", summary_df['total_trials'].iloc[0])
                    st.metric("Active Trials", summary_df['active_trials'].iloc[0])
                
                with col2:
                    st.metric("Unique Diseases", summary_df['unique_diseases'].iloc[0])
                    st.metric("Biomarker Trials", summary_df['biomarker_trial_count'].iloc[0])
                
                with col3:
                    st.metric("Avg Success Probability", 
                             f"{summary_df['avg_success_probability'].iloc[0]:.2%}")
                    st.metric("Avg Market Reaction", 
                             f"{summary_df['avg_market_reaction'].iloc[0]:.1f}/10")

                # Financial metrics
                st.subheader("Portfolio Financial Analysis")
                fin_col1, fin_col2, fin_col3 = st.columns(3)
                
                with fin_col1:
                    st.metric("Portfolio Value", 
                             f"${summary_df['portfolio_value_millions'].iloc[0]:,.1f}M")
                
                with fin_col2:
                    st.metric("Development Cost", 
                             f"${summary_df['portfolio_cost_millions'].iloc[0]:,.1f}M")
                
                with fin_col3:
                    st.metric("Expected Return", 
                             f"${summary_df['portfolio_return_millions'].iloc[0]:,.1f}M")

            # Get detailed trial information
            trials_df = search_sponsor(conn, sponsor_name)
            if trials_df is not None and not trials_df.empty:
                st.subheader("Clinical Trials Details")
                
                # Create tabs for different views
                tab1, tab2, tab3 = st.tabs(["Trial List", "Success Analysis", "Market Analysis"])
                
                with tab1:
                    st.dataframe(trials_df[['nct_id', 'brief_title', 'phase', 
                                          'status', 'disease_area', 'completion_date']])
                
                with tab2:
                    # Success probability by phase
                    fig1 = px.bar(trials_df, x='phase', y='phase_success_probability',
                                 title='Success Probability by Phase',
                                 labels={'phase_success_probability': 'Success Probability'})
                    st.plotly_chart(fig1)
                
                with tab3:
                    # Market reaction analysis
                    fig2 = px.scatter(trials_df, x='value_millions', y='ctmis_score',
                                    color='phase', size='return_millions',
                                    hover_data=['brief_title'],
                                    title='Market Value vs CTMIS Score')
                    st.plotly_chart(fig2)

                # Download option
                csv = trials_df.to_csv(index=False)
                st.download_button(
                    label="Download Trial Data as CSV",
                    data=csv,
                    file_name=f"{sponsor_name}_trials.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()
