import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

# Configure page
st.set_page_config(page_title="Clinical Trial Outcome Predictor", layout="wide")

# Database connection using st.secrets
@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=st.secrets["postgresql"]["host"],
        port=st.secrets["postgresql"]["port"],
        database=st.secrets["postgresql"]["database"],
        user=st.secrets["postgresql"]["user"],
        password=st.secrets["postgresql"]["password"]
    )

try:
    conn = init_connection()
    st.success("Successfully connected to the database!")
except Exception as e:
    st.error(f"Unable to connect to the database: {str(e)}")

st.title("Clinical Data Analysis")
