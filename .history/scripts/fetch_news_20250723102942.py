# scripts/fetch_news.py
import requests
import json
import sqlite3
from datetime import datetime
# fetch_news.py
from dotenv import load_dotenv
import os

# Load API key from .env
load_dotenv("D:\GitHub\global-news\.env")
API_KEY = os.getenv("NEWSAPI_KEY")


# Constants
API_URL = "https://newsapi.org/v2/top-headlines"
DB_PATH = "../data/news_sentiment.db"


def fetch_news(countries=["us", "gb", "in", "cn", "br"]):
    """Fetch headlines from NewsAPI for specified countries."""
    all_articles = []

    for country in countries:
        params = {
            "country": country,
            "apiKey": NEWS_API_KEY,
            "pageSize": 100  # Max allowed per request
        }
        response = requests.get(API_URL, params=params)

        if response.status_code == 200:
            articles = response.json().get("articles", [])
            for article in articles:
                article["country"] = country  # Add country code
            all_articles.extend(articles)
        else:
            print(f"Error fetching {country}: {response.status_code}")

    return all_articles


def save_to_db(articles):
    """Save articles to SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        author TEXT,
        title TEXT,
        description TEXT,
        url TEXT,
        published_at DATETIME,
        content TEXT,
        country TEXT
    )
    """)

    # Insert new articles
    for article in articles:
        cursor.execute("""
        INSERT INTO news (
            source, author, title, description, url, published_at, content, country
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article["source"]["name"],
            article.get("author"),
            article["title"],
            article.get("description"),
            article["url"],
            article["publishedAt"],
            article.get("content"),
            article["country"]
        ))

    conn.commit()
    conn.close()
    print(f"Saved {len(articles)} articles to DB.")


if __name__ == "__main__":
    articles = fetch_news()
    save_to_db(articles)
