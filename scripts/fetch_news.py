# scripts/fetch_news.py
import requests
from datetime import datetime
from db_utils import get_db_connection
from dotenv import load_dotenv
import os

load_dotenv('../config/.env')
API_KEY = os.getenv("NEWSAPI_KEY")


def fetch_news(countries=["us", "gb"]):
    all_articles = []
    for country in countries:
        params = {
            "country": country,
            "apiKey": API_KEY,
            "pageSize": 100
        }
        response = requests.get(
            "https://newsapi.org/v2/top-headlines", params=params)
        if response.ok:
            articles = response.json().get("articles", [])
            for article in articles:
                article["country"] = country
            all_articles.extend(articles)
    return all_articles


def save_to_db(articles):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for article in articles:
                cur.execute("""
                    INSERT INTO news (
                        source, author, title, description, url, 
                        published_at, content, country
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING
                    """, (
                    article["source"]["name"],
                    article.get("author"),
                    article["title"],
                    article.get("description"),
                    article["url"],
                    datetime.strptime(
                        article["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"),
                    article.get("content"),
                    article["country"]
                ))
        conn.commit()


if __name__ == "__main__":
    articles = fetch_news()
    save_to_db(articles)
    print(f"Processed {len(articles)} articles")
