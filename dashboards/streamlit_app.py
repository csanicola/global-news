import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("🌍 World News Sentiment Dashboard")
df = pd.read_csv("data/processed/daily_summary.csv")

st.line_chart(df[['date', 'avg_sentiment']])
st.bar_chart(df['top_topics'].value_counts().head(5))
