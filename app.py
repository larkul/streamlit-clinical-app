import streamlit as st
import pandas as pd
from datetime import datetime
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

def get_sponsor_suggestions(conn, partial_name):
    query = """
    SELECT DISTINCT sponsor_name 
    FROM streamlit_ctmis_view 
    WHERE LOWER(sponsor_name) LIKE LOWER(%s)
    LIMIT 10
    """
    df = execute_query(conn, query, [f"%{partial_name}%"])
    return df['sponsor_name'].tolist() if df is not None else []

def main():
    st.title("Clinical Trials Analysis Dashboard")
    
    # Initialize connection
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

    # Company size filter
    company_sizes = st.sidebar.multiselect(
        "Company Size",
        ["Small", "Medium", "Big"]
    )

    # Get unique disease areas for filter
    disease_query = "SELECT DISTINCT disease_area FROM streamlit_ctmis_view ORDER BY disease_area"
    diseases_df = execute_query(conn, disease_query)
    if diseases_df is not None:
        selected_diseases = st.sidebar.multiselect(
            "Disease Areas",
            options=diseases_df['disease_area'].dropna().unique()
        )

    # Phase filter
    phases = st.sidebar.multiselect(
        "Phases",
        ["PHASE1", "PHASE2", "PHASE3", "FDA_REVIEW"]
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

    # Sponsor search with autocomplete
    sponsor_input = st.text_input("Start typing sponsor name...")
    if sponsor_input:
        suggestions = get_sponsor_suggestions(conn, sponsor_input)
        if suggestions:
            sponsor_name = st.selectbox("Select sponsor", suggestions)
        else:
            sponsor_name = sponsor_input
    else:
        sponsor_name = None

    if sponsor_name:
        # Build query conditions
        conditions = ["LOWER(sponsor_name) LIKE LOWER(%s)"]
        params = [f"%{sponsor_name}%"]

        if start_date and end_date:
            conditions.append("completion_date BETWEEN %s AND %s")
            params.extend([start_date, end_date])

        if company_sizes:
            conditions.append("company_size = ANY(%s)")
            params.append(company_sizes)

        if selected_diseases:
            conditions.append("disease_area = ANY(%s)")
            params.append(selected_diseases)

        if phases:
            conditions.append("phase = ANY(%s)")
            params.append(phases)

        if statuses:
            conditions.append("status = ANY(%s)")
            params.append(statuses)

        if market_reactions:
            conditions.append("market_reaction_strength = ANY(%s)")
            params.append(market_reactions)

        where_clause = " AND ".join(conditions)

        # Main query for trials
        query = f"""
        SELECT 
            nct_id,
            brief_title,
            disease_area,
            phase,
            status,
            completion_date,
            phase_success_probability,
            likelihood_of_approval,
            market_reaction_strength,
            estimated_market_value/1000000 as market_value_millions,
            estimated_development_cost/1000000 as development_cost_millions,
            expected_return/1000000 as expected_return_millions
        FROM streamlit_ctmis_view
        WHERE {where_clause}
        ORDER BY completion_date DESC
        """

        trials_df = execute_query(conn, query, params)

        if trials_df is not None and not trials_df.empty:
            # Format the dataframe
            display_df = trials_df.copy()
            display_df['completion_date'] = pd.to_datetime(display_df['completion_date']).dt.strftime('%Y-%m-%d')
            display_df['phase_success_probability'] = display_df['phase_success_probability'].apply(lambda x: f"{x:.1%}" if pd.notnull(x) else "N/A")
            display_df['likelihood_of_approval'] = display_df['likelihood_of_approval'].apply(lambda x: f"{x:.1%}" if pd.notnull(x) else "N/A")
            display_df['market_value_millions'] = display_df['market_value_millions'].apply(lambda x: f"${x:,.1f}M" if pd.notnull(x) else "N/A")
            display_df['development_cost_millions'] = display_df['development_cost_millions'].apply(lambda x: f"${x:,.1f}M" if pd.notnull(x) else "N/A")
            display_df['expected_return_millions'] = display_df['expected_return_millions'].apply(lambda x: f"${x:,.1f}M" if pd.notnull(x) else "N/A")

            # Display the trials table
            st.dataframe(
                display_df,
                hide_index=True,
                column_config={
                    "nct_id": "NCT ID",
                    "brief_title": "Trial Title",
                    "disease_area": "Disease Area",
                    "phase": "Phase",
                    "status": "Status",
                    "completion_date": "Completion Date",
                    "phase_success_probability": "Phase Success Probability",
                    "likelihood_of_approval": "Likelihood of Approval",
                    "market_reaction_strength": "Market Reaction",
                    "market_value_millions": "Market Value",
                    "development_cost_millions": "Development Cost",
                    "expected_return_millions": "Expected Return"
                }
            )

            # Add download button
            csv = trials_df.to_csv(index=False)
            st.download_button(
                label="Download Data as CSV",
                data=csv,
                file_name=f"{sponsor_name}_trials.csv",
                mime="text/csv"
            )
        else:
            st.warning("No trials found matching the selected criteria.")

if __name__ == "__main__":
    main()