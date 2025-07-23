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

# 1. Sentiment Analysis Function


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

# 2. Emotion Lexicon Loading


def load_emotion_lexicon():
    """Load NRC Emotion Lexicon from new URL"""
    try:
        url = "https://raw.githubusercontent.com/HamidNE/sentiment-analysis-with-lexicon/refs/heads/master/NRC.csv"
        response = requests.get(url)
        response.raise_for_status()

        # Read CSV with correct formatting
        nrc_data = pd.read_csv(StringIO(response.text), header=None, names=[
                               'word', 'emotion', 'association'])
        emotion_dict = defaultdict(list)

        # Filter for words with positive association
        for _, row in nrc_data[nrc_data['association'] == 1].iterrows():
            emotion_dict[row['word']].append(row['emotion'])

        logger.info(
            f"Successfully loaded lexicon with {len(emotion_dict)} emotion words")
        return emotion_dict

    except Exception as e:
        logger.error(f"Lexicon loading failed: {str(e)}")
        logger.info("Using comprehensive fallback lexicon")
        return {
            'happy': ['joy'], 'joy': ['joy'], 'happiness': ['joy'],
            'love': ['joy', 'trust'], 'loved': ['joy', 'trust'],
            'best': ['joy'], 'better': ['joy'], 'great': ['joy'],
            'excited': ['joy', 'surprise'], 'excitement': ['joy', 'surprise'],
            'wonderful': ['joy'], 'awesome': ['joy'], 'fantastic': ['joy'],
            'angry': ['anger'], 'anger': ['anger'], 'mad': ['anger'],
            'furious': ['anger'], 'rage': ['anger'], 'annoyed': ['anger'],
            'sad': ['sadness'], 'sadness': ['sadness'], 'depressed': ['sadness'],
            'unhappy': ['sadness'], 'grief': ['sadness'], 'mourning': ['sadness'],
            'fear': ['fear'], 'scared': ['fear'], 'terrified': ['fear'],
            'anxious': ['fear'], 'nervous': ['fear'], 'worried': ['fear'],
            'surprise': ['surprise'], 'surprised': ['surprise'], 'shock': ['surprise'],
            'amazed': ['surprise'], 'disgust': ['disgust'], 'disgusted': ['disgust'],
            'trust': ['trust'], 'trusted': ['trust'], 'hopeful': ['trust'],
            'anticipation': ['anticipation'], 'waiting': ['anticipation']
        }


# Load lexicon at startup
emotion_dict = load_emotion_lexicon()

# 3. Enhanced Emotion Analysis


def analyze_emotions(text):
    """Robust emotion analysis with word normalization"""
    if not isinstance(text, str) or not text.strip():
        return None

    emotion_scores = defaultdict(float)
    words = text.lower().split()
    total_valid_words = 0

    for word in words:
        # Normalize word by removing punctuation and simple stemming
        clean_word = word.strip(".,!?;:\"'()[]").rstrip(
            's').rstrip('ed').rstrip('ing')
        if clean_word in emotion_dict:
            total_valid_words += 1
            for emotion in emotion_dict[clean_word]:
                emotion_scores[emotion] += 1

    if total_valid_words > 0:
        # Convert to percentage and round
        return {emotion: round(score/total_valid_words, 4)
                for emotion, score in emotion_scores.items()}

    logger.debug(f"No emotional words found in: {text[:100]}...")
    return None

# 4. Article Processing


def process_articles():
    """Process articles with verification logging"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verify table structure
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'news' 
                    AND column_name = 'emotions'
                """)
                if not cur.fetchone():
                    cur.execute("ALTER TABLE news ADD COLUMN emotions JSONB")
                    conn.commit()
                    logger.info("Added emotions column to table")

                # Get test articles
                cur.execute("""
                    SELECT id, title, description, content 
                    FROM news 
                    WHERE sentiment_score IS NULL 
                    OR emotions IS NULL
                    LIMIT 10
                """)
                articles = cur.fetchall()

                if not articles:
                    logger.info("No unprocessed articles found")
                    return 0

                processed_count = 0
                for article in articles:
                    article_id, title, description, content = article
                    text = " ".join(filter(None, [
                        str(title) if title else "",
                        str(description) if description else "",
                        str(content) if content else ""
                    ]))

                    if not text.strip():
                        continue

                    # Run analyses
                    polarity, sentiment = analyze_sentiment(text)
                    emotions = analyze_emotions(text)

                    # Debug logging
                    logger.debug(f"\n--- Article {article_id} ---")
                    logger.debug(f"Text: {text[:200]}...")
                    logger.debug(f"Sentiment: {sentiment} ({polarity:.2f})")
                    logger.debug(f"Emotions: {emotions}")

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
                    processed_count += 1

                conn.commit()
                logger.info(
                    f"Successfully processed {processed_count} articles")
                return processed_count

    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        raise


# Main execution
if __name__ == "__main__":
    load_dotenv('../config/.env')
    logger.info("Starting analysis with verified lexicon...")

    # Test with known emotional text
    test_phrases = [
        ("I love this wonderful happy day", "Should detect joy/love"),
        ("This angry furious rage makes me mad", "Should detect anger"),
        ("The fearful anxious worried crowd", "Should detect fear"),
        ("Empty text", None)
    ]

    for text, desc in test_phrases:
        logger.info(f"\nTest: {desc}")
        logger.info(f"Text: {text}")
        logger.info(f"Emotions: {analyze_emotions(text)}")

    # Process articles
    processed_count = process_articles()
    logger.info(f"Completed. Processed {processed_count} articles")
