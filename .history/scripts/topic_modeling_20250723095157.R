library(tidytext)
library(topicmodels)

# Assuming cleaned_df is a dataframe of tokenized headlines
dtm <- DocumentTermMatrix(cleaned_df)
lda_model <- LDA(dtm, k = 5)
topics <- tidy(lda_model, matrix = "beta")
