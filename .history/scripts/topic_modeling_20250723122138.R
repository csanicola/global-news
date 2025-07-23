# topic_modeling.R
library(tidyverse)
library(tidytext)
library(topicmodels)
library(DBI)

# Connect to PostgreSQL
con <- dbConnect(RPostgres::Postgres(),
                 dbname = Sys.getenv("DB_NAME"),
                 host = Sys.getenv("DB_HOST"),
                 port = Sys.getenv("DB_PORT"),
                 user = Sys.getenv("DB_USER"),
                 password = Sys.getenv("DB_PASSWORD"))

# Get news data
news_data <- dbGetQuery(con, "
    SELECT id, title, content, sentiment_label, country 
    FROM news 
    WHERE content IS NOT NULL
")

# Preprocess text
news_tokens <- news_data %>%
    unnest_tokens(word, content) %>%
    anti_join(stop_words) %>%
    filter(!str_detect(word, "\\d")) %>%
    mutate(word = textstem::lemmatize_words(word))

# Create DTM
news_dtm <- news_tokens %>%
    count(id, word) %>%
    cast_dtm(id, word, n)

# LDA Model
lda_model <- LDA(news_dtm, k = 5, control = list(seed = 1234))

# Save topics
topics <- tidy(lda_model, matrix = "beta")
dbWriteTable(con, "news_topics", topics, overwrite = TRUE)

dbDisconnect(con)