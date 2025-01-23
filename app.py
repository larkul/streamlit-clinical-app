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

def get_sponsor_details(conn, sponsor_name, filters):
    query = """
    SELECT 
        nct_id,
        sponsor_name,
        phase,
        status,
        disease_area,
        completion_date,
        phase_success_probability as probability_of_success,
        likelihood_of_approval,
        market_reaction_level as market_reaction, -- Use the precomputed level
        estimated_market_value/1000000 as market_value_millions,
        estimated_development_cost/1000000 as development_cost_millions,
        expected_return/1000000 as discount
    FROM streamlit_ctmis_view
    WHERE LOWER(sponsor_name) LIKE LOWER(%s)
    """

    # Apply additional filters
    params = [f'%{sponsor_name}%']

    if filters.get("disease_area"):
        query += " AND disease_area = %s"
        params.append(filters["disease_area"])

    if filters.get("phase"):
        query += " AND phase = %s"
        params.append(filters["phase"])

    if filters.get("status"):
        query += " AND status = %s"
        params.append(filters["status"])

    if filters.get("market_reaction"):
        query += " AND market_reaction_level = %s"
        params.append(filters["market_reaction"])  # Directly match Weak/Moderate/Strong

    if filters.get("has_biomarker"):
        query += " AND has_biomarker = TRUE"

    query += " ORDER BY completion_date ASC;"

    return execute_query(conn, query, params)

def main():
    st.title("Clinical Trials Analysis Dashboard")
    conn = init_connection()

    # Sidebar Filters
    st.sidebar.header("Filters")
    sponsor_name = st.text_input("Enter Sponsor Name")

    disease_area = st.sidebar.selectbox("Disease Area", ["", "Oncology", "Cardiology", "Neurology"])
    phase = st.sidebar.selectbox("Phase", ["", "PHASE1", "PHASE2", "PHASE3"])
    status = st.sidebar.selectbox("Status", ["", "RECRUITING", "ACTIVE", "ACTIVE_NOT_RECRUITING"])
    market_reaction = st.sidebar.selectbox("Market Reaction", ["", "Weak", "Moderate", "Strong"])
    has_biomarker = st.sidebar.checkbox("Has Biomarker")

    filters = {
        "disease_area": disease_area if disease_area else None,
        "phase": phase if phase else None,
        "status": status if status else None,
        "market_reaction": market_reaction if market_reaction > 0 else None,
        "has_biomarker": has_biomarker
    }

    if sponsor_name:
        sponsor_details_df = get_sponsor_details(conn, sponsor_name, filters)

        if sponsor_details_df is not None and not sponsor_details_df.empty:
            # Make NCT ID clickable
            sponsor_details_df['nct_id'] = sponsor_details_df['nct_id'].apply(
                lambda x: f"[Link](https://clinicaltrials.gov/study/{x})" if x else "N/A"
            )

            # Display the table
            st.header("Sponsor Details")
            st.dataframe(sponsor_details_df)

            st.caption(
                "**Columns Explained:**\n"
                "- **Phase:** Clinical trial phase (1, 2, or 3).\n"
                "- **Status:** Current status of the trial.\n"
                "- **Disease Area:** Disease area being targeted by the trial.\n"
                "- **Completion Date:** Expected trial completion date.\n"
                "- **Probability of Success:** Estimated success probability of the trial.\n"
                "- **Likelihood of Approval:** Likelihood of regulatory approval.\n"
                "- **Market Reaction:** Estimated market reaction.\n"
                "- **Market Value:** Estimated market value in millions.\n"
                "- **Development Cost:** Estimated development cost in millions.\n"
                "- **Discount:** Expected return in millions.\n"
                "- **NCT ID:** Link to the trial on ClinicalTrials.gov."
            )
        else:
            st.warning("No data found for this sponsor.")

if __name__ == "__main__":
    main()
