import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

st.set_page_config(page_title="Clinical Trial Analysis Dashboard", layout="wide")

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
        cur = conn.cursor()
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        results = cur.fetchall()
        return pd.DataFrame([dict(row) for row in results])
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None

def get_sponsor_names(conn, _):
    query = """
    SELECT DISTINCT sponsor_name 
    FROM streamlit_ctmis_view
    WHERE sponsor_name IS NOT NULL 
    AND sponsor_name != ''
    ORDER BY sponsor_name;
    """
    df = execute_query(conn, query)
    return [""] + (df['sponsor_name'].tolist() if df is not None else [])

def get_sponsor_details(conn, sponsor_name, filters):
    query = """
    SELECT 
        nct_id,
        brief_title,
        phase,
        status,
        disease_area,
        completion_date,
        phase_success_probability as probability_of_success,
        likelihood_of_approval,
        market_reaction_strength,
        estimated_market_value/1000000 as market_value_millions,
        estimated_development_cost/1000000 as development_cost_millions,
        expected_return/1000000 as expected_return_millions
    FROM streamlit_ctmis_view
    WHERE LOWER(sponsor_name) LIKE LOWER(%s)
    """

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
        query += " AND market_reaction_strength = %s"
        params.append(filters["market_reaction"])

    if filters.get("has_biomarker"):
        query += " AND has_biomarker = TRUE"

    query += " ORDER BY completion_date DESC;"
    return execute_query(conn, query, params)

def main():
    st.title("Clinical Trials Analysis Dashboard")
    conn = init_connection()

    # All filters in sidebar
    st.sidebar.header("Filters")
    
    # Autocomplete text input for sponsor
    sponsor_names = get_sponsor_names(conn, "")
    sponsor_name = st.sidebar.text_input(
        "Search Sponsor",
        key="sponsor_search"
    )
    
    # Filter sponsor names based on input
    matching_sponsors = [
        s for s in sponsor_names 
        if sponsor_name.lower() in s.lower()
    ] if sponsor_name else []
    
    if matching_sponsors:
        selected_sponsor = st.sidebar.selectbox(
            "Select from matching sponsors",
            options=matching_sponsors
        )
    else:
        selected_sponsor = ""

    disease_area = st.sidebar.selectbox(
        "Disease Area", 
        ["", "ONCOLOGY", "CARDIOVASCULAR", "NEUROLOGY", "INFECTIOUS_DISEASE", 
         "AUTOIMMUNE", "RESPIRATORY", "ENDOCRINE", "CNS", "GENITOURINARY", 
         "METABOLIC", "RARE_DISEASES", "OPHTHALMOLOGY", "VACCINES", "OTHER"]
    )
    
    phase = st.sidebar.selectbox("Phase", ["", "PHASE1", "PHASE2", "PHASE3"])
    status = st.sidebar.selectbox(
        "Status", 
        ["", "RECRUITING", "ACTIVE", "ACTIVE_NOT_RECRUITING"]
    )
    market_reaction = st.sidebar.selectbox(
        "Market Reaction", 
        ["", "Weak", "Moderate", "Strong"]
    )
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
            display_df = sponsor_details_df.copy()
            
            display_df['completion_date'] = pd.to_datetime(display_df['completion_date']).dt.strftime('%Y-%m-%d')
            numeric_cols = ['probability_of_success', 'likelihood_of_approval', 
                          'market_value_millions', 'development_cost_millions', 'expected_return_millions']
            
            for col in numeric_cols:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{x:.1%}" if col in ['probability_of_success', 'likelihood_of_approval']
                        else f"${x:,.1f}M" if pd.notnull(x) else "N/A"
                    )

            display_df['nct_id'] = display_df['nct_id'].apply(
                lambda x: f"[{x}](https://clinicaltrials.gov/study/{x})" if x else "N/A"
            )

            st.header("Sponsor Details")

            column_descriptions = {
                'probability_of_success': "The estimated probability (%) of the trial succeeding based on historical data for similar trials in the same phase and indication.",
                'likelihood_of_approval': "The probability (%) of receiving regulatory approval, considering the current phase and therapeutic area.",
                'market_reaction_strength': "Expected market response (Weak/Moderate/Strong) based on analysis of similar approved drugs and market conditions.",
                'market_value_millions': "Estimated market value in millions USD, calculated using market size, competition, and pricing analysis.",
                'development_cost_millions': "Estimated development costs in millions USD, including clinical trial costs, regulatory submissions, and other development expenses.",
                'expected_return_millions': "Expected return in millions USD, calculated as (Market Value × Likelihood of Approval) - Development Cost"
            }

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### Column Descriptions:")
                for col, desc in column_descriptions.items():
                    if col in display_df.columns:
                        with st.expander(f"ℹ️ {col.replace('_', ' ').title()}"):
                            st.write(desc)

            st.dataframe(display_df)

            csv = sponsor_details_df.to_csv(index=False)
            st.download_button(
                "Download Data as CSV",
                csv,
                f"{selected_sponsor}_trials.csv",
                "text/csv"
            )
        else:
            st.warning("No data found for this sponsor.")

if __name__ == "__main__":
    main()
