# scripts/analyze_sentiment.py
import psycopg2
import pandas as pd
from textblob import TextBlob
from dotenv import load_dotenv
import os
from db_utils import get_db_connection
import logging
from collections import defaultdict
import requests
from io import StringIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. First define all analysis functions


def analyze_sentiment(text):
    """TextBlob sentiment analysis"""
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity

    if polarity > 0.1:
        sentiment = 'positive'
    elif polarity < -0.1:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'

    return polarity, sentiment


def load_emotion_lexicon():
    """Load NRC Emotion Lexicon"""
    try:
        url = "https://raw.githubusercontent.com/ian-nai/In-Class-Exercise-Data/main/nrc_emotion_lexicon.csv"
        response = requests.get(url)
        response.raise_for_status()

        nrc_data = pd.read_csv(StringIO(response.text))
        emotion_dict = defaultdict(list)

        for _, row in nrc_data.iterrows():
            if row['association'] == 1:
                emotion_dict[row['word']].append(row['emotion'])

        logger.info(f"Loaded emotion lexicon with {len(emotion_dict)} words")
        return emotion_dict

    except Exception as e:
        logger.error(f"Failed to load emotion lexicon: {str(e)}")
        return None


# Load lexicon at startup
emotion_dict = load_emotion_lexicon()


def analyze_emotions(text):
    """Emotion analysis using NRC lexicon"""
    if not emotion_dict:
        return None

    emotion_scores = defaultdict(float)
    words = text.lower().split()
    total_valid_words = 0

    for word in words:
        if word in emotion_dict:
            total_valid_words += 1
            for emotion in emotion_dict[word]:
                emotion_scores[emotion] += 1

    if total_valid_words > 0:
        for emotion in emotion_scores:
            emotion_scores[emotion] = round(
                emotion_scores[emotion] / total_valid_words, 4)
        return dict(emotion_scores)

    return None

# 2. Then define the processing function


def process_articles():
    """Process articles with both analyses"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check/Add emotion columns if missing
                try:
                    cur.execute("""
                        ALTER TABLE news 
                        ADD COLUMN IF NOT EXISTS emotions JSONB
                    """)
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Column check failed: {str(e)}")

                cur.execute("""
                    SELECT id, title, description, content 
                    FROM news 
                    WHERE sentiment_score IS NULL
                """)
                articles = cur.fetchall()

                if not articles:
                    logger.info("No unprocessed articles found")
                    return 0

                for article in articles:
                    article_id, title, description, content = article
                    text = " ".join(
                        filter(None, [str(title), str(description), str(content)]))

                    logger.info(f"Processing article {article_id}")

                    # Sentiment analysis
                    polarity, sentiment = analyze_sentiment(text)

                    # Emotion analysis
                    emotions = analyze_emotions(text)

                    cur.execute("""
                        UPDATE news 
                        SET sentiment_score = %s,
                            sentiment_label = %s,
                            emotions = %s
                        WHERE id = %s
                    """, (
                        polarity,
                        sentiment,
                        psycopg2.extras.Json(emotions) if emotions else None,
                        article_id
                    ))

                conn.commit()
                return len(articles)

    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise


# 3. Finally, the main execution
if __name__ == "__main__":
    load_dotenv('D:\GitHub\global-news\config\.env')
    logger.info("Starting analysis...")

    # Test with sample text
    test_text = "The happy children laughed with joy at the wonderful surprise"
    logger.info(f"\nTest analysis for: '{test_text}'")
    logger.info(f"Sentiment: {analyze_sentiment(test_text)}")
    logger.info(f"Emotions: {analyze_emotions(test_text)}")

    # Process articles
    processed_count = process_articles()
    logger.info(f"Completed. Processed {processed_count} articles")
