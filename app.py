import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

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

def get_all_sponsors(conn):
    query = "SELECT DISTINCT sponsor_name FROM streamlit_ctmis_view ORDER BY sponsor_name ASC;"
    return execute_query(conn, query)

def get_sponsor_details(conn, sponsor_name, filters):
    query = """
    SELECT 
        sponsor_name,
        phase,
        status,
        disease_area,
        completion_date,
        phase_success_probability as probability_of_success,
        likelihood_of_approval,
        market_reaction_level as market_reaction,
        estimated_market_value/1000000 as market_value_millions,
        estimated_development_cost/1000000 as development_cost_millions,
        expected_return/1000000 as discount,
        nct_id
    FROM streamlit_ctmis_view
    WHERE LOWER(sponsor_name) LIKE LOWER(%s)
    """

    params = [f"%{sponsor_name}%"]

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
        params.append(filters["market_reaction"])

    if filters.get("has_biomarker"):
        query += " AND has_biomarker = TRUE"

    query += " ORDER BY completion_date ASC;"

    return execute_query(conn, query, params)

def main():
    st.set_page_config(page_title="Clinical Trials Dashboard", layout="wide")

    conn = init_connection()

    st.title("Clinical Trials Analysis Dashboard")

    # Fetch all sponsor names for dynamic suggestions
    sponsor_names_df = get_all_sponsors(conn)
    sponsor_names = sponsor_names_df['sponsor_name'].tolist() if sponsor_names_df is not None else []

    # Sidebar filters
    st.sidebar.header("Filters")
    sponsor_name_input = st.sidebar.text_input("Search Sponsor Name")
    matching_sponsors = [name for name in sponsor_names if sponsor_name_input.lower() in name.lower()] if sponsor_name_input else sponsor_names
    selected_sponsor = st.sidebar.selectbox("Select Sponsor Name", matching_sponsors)

    disease_area = st.sidebar.selectbox("Disease Area", ["", "Oncology", "Cardiology", "Neurology"])
    phase = st.sidebar.selectbox("Phase", ["", "PHASE1", "PHASE2", "PHASE3"])
    status = st.sidebar.selectbox("Status", ["", "RECRUITING", "ACTIVE", "ACTIVE_NOT_RECRUITING"])
    market_reaction = st.sidebar.selectbox("Market Reaction", ["", "Weak", "Moderate", "Strong"])
    has_biomarker = st.sidebar.checkbox("Has Biomarker")

    filters = {
        "disease_area": disease_area if disease_area else None,
        "phase": phase if phase else None,
        "status": status if status else None,
        "market_reaction": market_reaction if market_reaction else None,
        "has_biomarker": has_biomarker
    }

    if selected_sponsor:
        sponsor_details_df = get_sponsor_details(conn, selected_sponsor, filters)

        if sponsor_details_df is not None and not sponsor_details_df.empty:
            # Make NCT ID clickable
            sponsor_details_df['nct_id'] = sponsor_details_df['nct_id'].apply(
                lambda x: f"[Link](https://clinicaltrials.gov/study/{x})" if x else "N/A"
            )

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
                "- **Market Reaction:** Categorized as Weak, Moderate, or Strong.\n"
                "- **Market Value:** Estimated market value in millions.\n"
                "- **Development Cost:** Estimated development cost in millions.\n"
                "- **Discount:** Expected return in millions.\n"
                "- **NCT ID:** Link to the trial on ClinicalTrials.gov."
            )
        else:
            st.warning("No data found for the selected sponsor and filters.")

if __name__ == "__main__":
    main()
