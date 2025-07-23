import os
import pandas as pd
from newsapi import NewsApiClient
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("NEWS_API_KEY")
newsapi = NewsApiClient(api_key=api_key)


def fetch_headlines(query="world", language="en"):
    all_articles = newsapi.get_everything(q=query,
                                          language=language,
                                          sort_by="publishedAt",
                                          page_size=100)
    articles = all_articles["articles"]
    df = pd.DataFrame([{
        "title": a["title"],
        "description": a["description"],
        "source": a["source"]["name"],
        "published": a["publishedAt"]
    } for a in articles])
    df.to_csv("data/raw/headlines.csv", index=False)
    print("Saved headlines to data/raw/headlines.csv")


if __name__ == "__main__":
    fetch_headlines()
