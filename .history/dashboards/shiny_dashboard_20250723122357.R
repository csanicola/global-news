# shiny_dashboard.R
library(shiny)
library(shinydashboard)
library(plotly)
library(DBI)
library(tidyverse)

ui <- dashboardPage(
    dashboardHeader(title = "News Sentiment Dashboard"),
    dashboardSidebar(
        selectInput("country", "Select Country:", 
                   choices = c("All", "US", "GB", "IN", "CN", "BR")),
        dateRangeInput("dates", "Date Range:", start = Sys.Date() - 30)
    )),
    dashboardBody(
        fluidRow(
            box(plotlyOutput("sentiment_trend"), width = 12
        )),
        fluidRow(
            box(plotlyOutput("emotion_radar"), width = 6,
            box(plotlyOutput("topic_bubbles"), width = 6
        )
    )
))

server <- function(input, output) {
    con <- dbConnect(RPostgres::Postgres(),
                    dbname = Sys.getenv("DB_NAME"),
                    host = Sys.getenv("DB_HOST"),
                    port = Sys.getenv("DB_PORT"),
                    user = Sys.getenv("DB_USER"),
                    password = Sys.getenv("DB_PASSWORD"))
    
    news_data <- reactive({
        query <- "
        SELECT published_at, sentiment_label, emotions, country 
        FROM news 
        WHERE published_at BETWEEN $1 AND $2
        "
        if (input$country != "All") {
            query <- paste(query, "AND country = $3")
            params <- list(input$dates[1], input$dates[2], tolower(input$country))
        } else {
            params <- list(input$dates[1], input$dates[2])
        }
        
        dbGetQuery(con, query, params)
    })
    
    output$sentiment_trend <- renderPlotly({
        data <- news_data() %>%
            mutate(date = as.Date(published_at)) %>%
            count(date, sentiment_label)
        
        plot_ly(data, x = ~date, y = ~n, color = ~sentiment_label, type = 'scatter', mode = 'lines')
    })
    
    output$emotion_radar <- renderPlotly({
        emotions <- news_data() %>%
            mutate(emotions = map(emotions, ~tibble(emotion = names(.), score = .))) %>%
            unnest(emotions) %>%
            group_by(emotion) %>%
            summarize(score = mean(score, na.rm = TRUE))
        
        plot_ly(emotions, type = 'scatterpolar', r = ~score, theta = ~emotion, fill = 'toself')
    })
    
    onStop(function() {
        dbDisconnect(con)
    })
}

shinyApp(ui, server)