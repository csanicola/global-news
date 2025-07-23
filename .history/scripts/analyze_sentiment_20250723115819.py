import psycopg2
from textblob import TextBlob
from dotenv import load_dotenv
import os
from db_utils import get_db_connection
import logging
from collections import defaultdict
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Comprehensive Emotion Lexicon (Direct Dictionary)
emotion_dict = {
    # Joy
    'happy': ['joy'], 'happiness': ['joy'], 'joy': ['joy'], 'joyful': ['joy'],
    'delight': ['joy'], 'delighted': ['joy'], 'cheerful': ['joy'], 'glad': ['joy'],
    'love': ['joy', 'trust'], 'loved': ['joy', 'trust'], 'lovely': ['joy'],
    'wonderful': ['joy'], 'awesome': ['joy'], 'fantastic': ['joy'], 'great': ['joy'],
    'best': ['joy'], 'better': ['joy'], 'excellent': ['joy'], 'amazing': ['joy'],

    # Anger
    'angry': ['anger'], 'anger': ['anger'], 'mad': ['anger'], 'furious': ['anger'],
    'rage': ['anger'], 'annoyed': ['anger'], 'irritated': ['anger'], 'frustrated': ['anger'],
    'outrage': ['anger'], 'aggravated': ['anger'],

    # Sadness
    'sad': ['sadness'], 'sadness': ['sadness'], 'unhappy': ['sadness'], 'depressed': ['sadness'],
    'grief': ['sadness'], 'mourning': ['sadness'], 'heartbroken': ['sadness'], 'melancholy': ['sadness'],

    # Fear
    'fear': ['fear'], 'scared': ['fear'], 'afraid': ['fear'], 'terrified': ['fear'],
    'anxious': ['fear'], 'nervous': ['fear'], 'worried': ['fear'], 'panicked': ['fear'],

    # Surprise
    'surprise': ['surprise'], 'surprised': ['surprise'], 'shock': ['surprise'], 'amazed': ['surprise'],
    'astonished': ['surprise'], 'astounded': ['surprise'],

    # Trust
    'trust': ['trust'], 'trusted': ['trust'], 'hopeful': ['trust'], 'confident': ['trust'],

    # Disgust
    'disgust': ['disgust'], 'disgusted': ['disgust'], 'revulsion': ['disgust'], 'contempt': ['disgust'],

    # Anticipation
    'anticipation': ['anticipation'], 'expectation': ['anticipation'], 'waiting': ['anticipation']
}

# 2. Enhanced Text Processing


def normalize_word(word):
    """Clean and normalize words for better matching"""
    word = word.lower().strip(".,!?;:\"'()[]")
    # Simple stemming
    if word.endswith('ing'):
        word = word[:-3]
    elif word.endswith('ed'):
        word = word[:-2]
    elif word.endswith('s'):
        word = word[:-1]
    return word

# 3. Emotion Analysis


def analyze_emotions(text):
    """Robust emotion analysis with direct dictionary matching"""
    if not isinstance(text, str) or not text.strip():
        return None

    emotion_scores = defaultdict(float)
    words = re.findall(r"\w+", text.lower())  # Better word splitting
    total_valid_words = 0

    for word in words:
        normalized = normalize_word(word)
        if normalized in emotion_dict:
            total_valid_words += 1
            for emotion in emotion_dict[normalized]:
                emotion_scores[emotion] += 1

    if total_valid_words > 0:
        # Convert counts to percentages
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
