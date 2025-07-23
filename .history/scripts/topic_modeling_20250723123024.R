# topic_modeling.R
library(tidyverse)
library(tidytext)
library(topicmodels)
library(DBI)
library(RPostgres)
library(dotenv)

# Load environment variables
load_dot_env("D:/GitHub/global-news/config/.env")

# Connect to PostgreSQL with explicit password
con <- dbConnect(
  Postgres(),
  dbname = Sys.getenv("DB_NAME"),
  host = Sys.getenv("DB_HOST"),
  port = Sys.getenv("DB_PORT"),
  user = Sys.getenv("DB_USER"),
  password = Sys.getenv("DB_PASSWORD")
)

# Verify connection
if (!dbIsValid(con)) {
  stop("Failed to connect to database")
} else {
  message("Successfully connected to PostgreSQL")
}

# Get news data with error handling
tryCatch({
  news_data <- dbGetQuery(con, "
    SELECT id, title, content, sentiment_label, country 
    FROM news 
    WHERE content IS NOT NULL
    LIMIT 1000  -- Process in batches
  ")
  
  # Preprocess text
  news_tokens <- news_data %>%
    unnest_tokens(word, content) %>%
    anti_join(stop_words) %>%
    filter(!str_detect(word, "\\d")) %>%
    mutate(word = textstem::lemmatize_words(word))
  
  # Create DTM if we have enough data
  if (nrow(news_tokens) > 100) {
    news_dtm <- news_tokens %>%
      count(id, word) %>%
      cast_dtm(id, word, n)
    
    # LDA Model
    lda_model <- LDA(news_dtm, k = 5, control = list(seed = 1234))
    
    # Save topics
    topics <- tidy(lda_model, matrix = "beta")
    dbWriteTable(con, "news_topics", topics, overwrite = TRUE)
    message("Successfully saved topics to database")
  } else {
    warning("Insufficient data for topic modeling")
  }
}, 
error = function(e) {
  message("Error during topic modeling: ", e$message)
},
finally = {
  dbDisconnect(con)
  message("Database connection closed")
})