import psycopg2
from dotenv import load_dotenv
import os
from contextlib import contextmanager

load_dotenv('../config/.env')


@contextmanager
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )
    try:
        yield conn
    finally:
        conn.close()
