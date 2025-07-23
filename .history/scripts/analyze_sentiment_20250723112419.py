# scripts/analyze_sentiment.py
import psycopg2
import pandas as pd
from textblob import TextBlob
from dotenv import load_dotenv
import os
from db_utils import get_db_connection
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load NRC Emotion Lexicon (first-time setup)
try:
    nrc_lexicon = pd.read_csv(
        "https://raw.githubusercontent.com/ian-nai/In-Class-Exercise-Data/main/nrc_emotion_lexicon.csv"
    )
    emotion_dict = defaultdict(list)
    for index, row in nrc_lexicon.iterrows():
        emotion_dict[row['word']].append(row['emotion'])
except Exception as e:
    logger.error(f"Failed to load emotion lexicon: {str(e)}")
    emotion_dict = None


def analyze_emotions(text):
    """
    Analyze emotions using NRC Emotion Lexicon
    Returns:
        dict: Emotion scores {anger: 0.2, joy: 0.5, ...}
    """
    if not emotion_dict:
        return None

    emotion_scores = defaultdict(float)
    words = text.lower().split()
    total_words = len(words) or 1  # Avoid division by zero

    for word in words:
        if word in emotion_dict:
            for emotion in emotion_dict[word]:
                emotion_scores[emotion] += 1/total_words

    return dict(emotion_scores)


def analyze_sentiment(text):
    """TextBlob sentiment analysis (unchanged)"""
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity

    if polarity > 0.1:
        sentiment = 'positive'
    elif polarity < -0.1:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'

    return polarity, sentiment


def process_articles():
    """Process articles with both sentiment and emotion analysis"""
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

                # Get unprocessed articles
                cur.execute("""
                    SELECT id, title, description, content 
                    FROM news 
                    WHERE sentiment_score IS NULL
                    LIMIT 500  # Smaller batch for emotion analysis
                """)
                articles = cur.fetchall()

                if not articles:
                    logger.info("No unprocessed articles found")
                    return 0

                updated_count = 0
                for article in articles:
                    article_id, title, description, content = article
                    text = " ".join(
                        filter(None, [title, description, content]))

                    if not text.strip():
                        continue

                    try:
                        # Sentiment analysis
                        polarity, sentiment = analyze_sentiment(text)

                        # Emotion analysis
                        emotions = analyze_emotions(text)

                        # Update database
                        cur.execute("""
                            UPDATE news 
                            SET sentiment_score = %s,
                                sentiment_label = %s,
                                emotions = %s
                            WHERE id = %s
                        """, (
                            polarity,
                            sentiment,
                            psycopg2.extras.Json(
                                emotions) if emotions else None,
                            article_id
                        ))
                        updated_count += 1

                    except Exception as e:
                        logger.error(
                            f"Error processing article {article_id}: {str(e)}")
                        continue

                conn.commit()
                logger.info(f"Processed {updated_count} articles")
                return updated_count

    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise


if __name__ == "__main__":
    load_dotenv('../config/.env')
    logger.info("Starting analysis with emotion detection...")
    processed_count = process_articles()
    logger.info(f"Completed. Processed {processed_count} articles")
