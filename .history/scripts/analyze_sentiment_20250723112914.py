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


def load_emotion_lexicon():
    """Load NRC Emotion Lexicon with better error handling"""
    try:
        # Download the lexicon
        url = "https://raw.githubusercontent.com/ian-nai/In-Class-Exercise-Data/main/nrc_emotion_lexicon.csv"
        response = requests.get(url)
        response.raise_for_status()

        # Process the data
        nrc_data = pd.read_csv(StringIO(response.text))
        emotion_dict = defaultdict(list)

        for _, row in nrc_data.iterrows():
            if row['association'] == 1:  # Only include words with strong association
                emotion_dict[row['word']].append(row['emotion'])

        logger.info(f"Loaded emotion lexicon with {len(emotion_dict)} words")
        return emotion_dict

    except Exception as e:
        logger.error(f"Failed to load emotion lexicon: {str(e)}")
        return None


# Load lexicon at startup
emotion_dict = load_emotion_lexicon()


def analyze_emotions(text):
    """
    Enhanced emotion analysis with debugging
    Returns:
        dict: Emotion scores or None if analysis fails
    """
    if not emotion_dict:
        logger.warning("Emotion lexicon not available")
        return None

    if not isinstance(text, str) or not text.strip():
        logger.warning("Empty text for emotion analysis")
        return None

    emotion_scores = defaultdict(float)
    words = text.lower().split()
    total_valid_words = 0

    for word in words:
        if word in emotion_dict:
            total_valid_words += 1
            for emotion in emotion_dict[word]:
                emotion_scores[emotion] += 1

    # Normalize scores if we found any emotional words
    if total_valid_words > 0:
        for emotion in emotion_scores:
            emotion_scores[emotion] = round(
                emotion_scores[emotion] / total_valid_words, 4)
        logger.debug(f"Emotion scores: {dict(emotion_scores)}")
        return dict(emotion_scores)

    logger.debug("No emotional words found in text")
    return None


def process_articles():
    """Process articles with enhanced error handling"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get sample articles for debugging
                cur.execute("""
                    SELECT id, title, description, content 
                    FROM news 
                    WHERE sentiment_score IS NULL
                    LIMIT 5  -- Small batch for testing
                """)
                articles = cur.fetchall()

                if not articles:
                    logger.info("No unprocessed articles found")
                    return 0

                for article in articles:
                    article_id, title, description, content = article
                    text = " ".join(
                        filter(None, [str(title), str(description), str(content)]))

                    logger.info(
                        f"\nProcessing article {article_id}:\nText: {text[:200]}...")

                    # Sentiment analysis
                    polarity, sentiment = analyze_sentiment(text)
                    logger.info(
                        f"Sentiment: {sentiment} (score: {polarity:.2f})")

                    # Emotion analysis
                    emotions = analyze_emotions(text)
                    logger.info(f"Emotions: {emotions}")

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
                        psycopg2.extras.Json(emotions) if emotions else None,
                        article_id
                    ))

                conn.commit()
                logger.info("Successfully processed batch")
                return len(articles)

    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise


if __name__ == "__main__":
    load_dotenv('D:\GitHub\global-news\config\.env')
    logger.info("Starting analysis with enhanced emotion detection...")

    # Test emotion analysis with sample text
    test_text = "The happy children laughed with joy at the wonderful surprise"
    logger.info("\n=== Testing with sample text ===")
    logger.info(f"Text: {test_text}")
    logger.info(f"Emotions: {analyze_emotions(test_text)}")

    # Process articles
    processed_count = process_articles()
    logger.info(f"Completed. Processed {processed_count} articles")
