import streamlit as st
import pandas as pd
import plotly.express as px
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
    
    # Initialize connection
    conn = init_connection()
    
    # Get sponsor name from user
    sponsor_name = st.text_input("Enter Sponsor Name:")
    
    if sponsor_name:
        # Get sponsor summary from the correct view
        summary_query = """
        SELECT 
            total_trials,
            active_trials,
            unique_diseases,
            biomarker_trial_count,
            avg_success_probability,
            avg_market_reaction,
            portfolio_value_millions,
            portfolio_cost_millions,
            portfolio_return_millions
        FROM get_sponsor_summary(%s)
        """
        
        summary_df = execute_query(conn, summary_query, [sponsor_name])
        
        if summary_df is not None and not summary_df.empty:
            # Display metrics in columns
            st.subheader("Portfolio Overview")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Trials", summary_df['total_trials'].iloc[0])
                st.metric("Active Trials", summary_df['active_trials'].iloc[0])
                st.metric("Unique Diseases", summary_df['unique_diseases'].iloc[0])
            
            with col2:
                st.metric("Average Success Probability", 
                         f"{summary_df['avg_success_probability'].iloc[0]:.1%}" 
                         if pd.notnull(summary_df['avg_success_probability'].iloc[0]) else "N/A")
                st.metric("Average Market Reaction", 
                         f"{summary_df['avg_market_reaction'].iloc[0]:.1f}/10"
                         if pd.notnull(summary_df['avg_market_reaction'].iloc[0]) else "N/A")
            
            with col3:
                st.metric("Portfolio Value", 
                         f"${summary_df['portfolio_value_millions'].iloc[0]:,.1f}M"
                         if pd.notnull(summary_df['portfolio_value_millions'].iloc[0]) else "N/A")
                st.metric("Expected Return", 
                         f"${summary_df['portfolio_return_millions'].iloc[0]:,.1f}M"
                         if pd.notnull(summary_df['portfolio_return_millions'].iloc[0]) else "N/A")
        
        # Get detailed trial information from streamlit_ctmis_view
        trials_query = """
        SELECT 
            nct_id,
            brief_title,
            phase,
            status,
            disease_area,
            completion_date,
            phase_success_probability,
            likelihood_of_approval,
            ctmis_score,
            market_reaction_level,
            market_reaction_strength,
            estimated_market_value/1000000 as value_millions,
            estimated_development_cost/1000000 as cost_millions,
            expected_return/1000000 as return_millions
        FROM search_sponsor(%s)
        """
        
        trials_df = execute_query(conn, trials_query, [sponsor_name])
        
        if trials_df is not None and not trials_df.empty:
            # Create tabs for different views
            tab1, tab2 = st.tabs(["Trial Overview", "Market Analysis"])
            
            with tab1:
                # Show active trials
                st.subheader("Active Trials")
                active_trials = trials_df[trials_df['status'].isin(['RECRUITING', 'ACTIVE', 'ACTIVE_NOT_RECRUITING'])]
                if not active_trials.empty:
                    st.dataframe(
                        active_trials[[
                            'nct_id', 'brief_title', 'phase', 'disease_area', 
                            'status', 'completion_date'
                        ]],
                        hide_index=True
                    )
                
                # Show completed trials
                st.subheader("Completed Trials")
                completed_trials = trials_df[trials_df['status'] == 'COMPLETED']
                if not completed_trials.empty:
                    st.dataframe(
                        completed_trials[[
                            'nct_id', 'brief_title', 'phase', 'disease_area', 
                            'completion_date'
                        ]],
                        hide_index=True
                    )
            
            with tab2:
                # Show market analysis in columns format
                st.subheader("Market Analysis and Success Probabilities")
                for _, trial in trials_df.iterrows():
                    with st.expander(f"{trial['brief_title']} ({trial['nct_id']})"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write("**Trial Details**")
                            st.write(f"Phase: {trial['phase']}")
                            st.write(f"Disease Area: {trial['disease_area']}")
                            st.write(f"Status: {trial['status']}")
                        
                        with col2:
                            st.write("**Success Metrics**")
                            st.write(f"Phase Success Probability: {trial['phase_success_probability']:.1%}")
                            st.write(f"Likelihood of Approval: {trial['likelihood_of_approval']:.1%}")
                            st.write(f"CTMIS Score: {trial['ctmis_score']:.1f}/10")
                            st.write(f"Market Reaction: {trial['market_reaction_strength']}")
                        
                        with col3:
                            st.write("**Financial Metrics**")
                            st.write(f"Market Value: ${trial['value_millions']:,.1f}M")
                            st.write(f"Development Cost: ${trial['cost_millions']:,.1f}M")
                            st.write(f"Expected Return: ${trial['return_millions']:,.1f}M")

                # Add download button for the full dataset
                csv = trials_df.to_csv(index=False)
                st.download_button(
                    label="Download Full Analysis as CSV",
                    data=csv,
                    file_name=f"{sponsor_name}_analysis.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()