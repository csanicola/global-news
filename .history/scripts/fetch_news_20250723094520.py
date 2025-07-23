# fetch_news.py
from newsapi import NewsApiClient
import pandas as pd

api = NewsApiClient(api_key='YOUR_API_KEY')


def fetch_headlines(query='world', language='en'):
    headlines = api.get_everything(
        q=query, language=language, sort_by='publishedAt', page_size=100)
    return pd.DataFrame([{
        "title": article["title"],
        "description": article["description"],
        "source": article["source"]["name"],
        "published": article["publishedAt"]
    } for article in headlines['articles']])
