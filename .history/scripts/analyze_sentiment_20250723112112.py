import psycopg2
from textblob import TextBlob
from dotenv import load_dotenv
import os
from db_utils import get_db_connection
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_sentiment(text):
    """
    Analyze sentiment using TextBlob
    Returns:
        tuple: (polarity, sentiment_label)
        polarity: float between -1 (negative) and 1 (positive)
        sentiment_label: 'positive', 'negative', or 'neutral'
    """
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
    """Fetch unprocessed articles and update with sentiment analysis"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get articles without sentiment analysis
                cur.execute("""
                    SELECT id, title, description, content 
                    FROM news 
                    WHERE sentiment_score IS NULL
                    LIMIT 1000  # Process in batches
                """)
                articles = cur.fetchall()

                if not articles:
                    logger.info("No unprocessed articles found")
                    return 0

                updated_count = 0
                for article in articles:
                    article_id, title, description, content = article

                    # Combine fields for analysis
                    text = " ".join(
                        filter(None, [title, description, content]))
                    if not text.strip():
                        continue

                    try:
                        polarity, sentiment = analyze_sentiment(text)

                        # Update the database
                        cur.execute("""
                            UPDATE news 
                            SET sentiment_score = %s, 
                                sentiment_label = %s 
                            WHERE id = %s
                        """, (polarity, sentiment, article_id))
                        updated_count += 1

                    except Exception as e:
                        logger.error(
                            f"Error processing article {article_id}: {str(e)}")
                        continue

                conn.commit()
                logger.info(f"Successfully processed {updated_count} articles")
                return updated_count

    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise


if __name__ == "__main__":
    load_dotenv('D:\GitHub\global-news\config\.env')
    logger.info("Starting sentiment analysis...")
    processed_count = process_articles()
    logger.info(f"Completed. Processed {processed_count} articles")
