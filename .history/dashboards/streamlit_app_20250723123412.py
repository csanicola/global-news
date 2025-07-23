# streamlit_app.py
import streamlit as st
import plotly.express as px
import pandas as pd
from db_utils import get_db_connection
import json

st.set_page_config(layout="wide")

# Sidebar controls
st.sidebar.title("Filters")
country = st.sidebar.selectbox("Country", ["All", "US", "GB", "IN", "CN", "BR"])
date_range = st.sidebar.date_input("Date Range", [])

# Connect to database
conn = get_db_connection()

# Load data
query = """
    SELECT published_at, sentiment_label, emotions, country 
    FROM news
"""
params = []

if country != "All":
    query += " WHERE country = %s"
    params.append(country.lower())

if len(date_range) == 2:
    if "WHERE" not in query:
        query += " WHERE"
    else:
        query += " AND"
    query += " published_at BETWEEN %s AND %s"
    params.extend(date_range)

df = pd.read_sql(query, conn, params=params if params else None)

# Process emotions data
if not df.empty and 'emotions' in df.columns:
    emotions_df = pd.json_normalize(df['emotions'].apply(
        lambda x: json.loads(x) if x else {}
    ))
    emotions_agg = emotions_df.mean().reset_index()
    emotions_agg.columns = ['emotion', 'score']

# Dashboard
st.title("Global News Sentiment Dashboard")

# Row 1: Sentiment Trend
st.subheader("Sentiment Over Time")
df['date'] = pd.to_datetime(df['published_at']).dt.date
sentiment_counts = df.groupby(['date', 'sentiment_label']).size().unstack()
st.line_chart(sentiment_counts)

# Row 2: Emotion and Topics
col1, col2 = st.columns(2)

with col1:
    st.subheader("Emotion Analysis")
    if not df.empty and 'emotions' in df.columns:
        fig = px.line_polar(emotions_agg, r='score', theta='emotion', line_close=True)
        st.plotly_chart(fig)

with col2:
    st.subheader("Topic Distribution")
    topics_df = pd.read_sql("SELECT * FROM news_topics", conn)
    if not topics_df.empty:
        top_terms = topics_df.groupby('topic').apply(
            lambda x: x.nlargest(5, 'beta')['term'].tolist()
        )
        st.write(top_terms)

conn.close()