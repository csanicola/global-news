-- Setup database and tables (run once)
CREATE TABLE IF NOT EXISTS news (
    id SERIAL PRIMARY KEY,
    source TEXT,
    author TEXT,
    title TEXT,
    description TEXT,
    url TEXT UNIQUE,          -- Prevent duplicates
    published_at TIMESTAMP,
    content TEXT,
    country VARCHAR(2),
    sentiment_score FLOAT,
    sentiment_label VARCHAR(8)
);

-- Add indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_country ON news(country);
CREATE INDEX IF NOT EXISTS idx_published ON news(published_at);