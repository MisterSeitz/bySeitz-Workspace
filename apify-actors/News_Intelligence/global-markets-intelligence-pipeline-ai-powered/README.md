# 📈 Global Markets Intelligence Pipeline

This actor is an automated market intelligence platform that aggregates financial news from both traditional RSS feeds and the Alpha Vantage API. It enriches every article with real-time context from the Google Programmable Search API and then uses the Gemini LLM to deliver structured, actionable insights on market sentiment, trends, and key entities.

---

## Features

-   **Dual-Source Aggregation**: Fetches data from a wide array of categorized financial RSS feeds and directly from the Alpha Vantage financial news API for comprehensive coverage.
-   **Real-Time Grounding**: Every article from every source is run through the Google Programmable Search API to gather the latest context before analysis.
-   **Advanced Market Analysis**: Uses Google's Gemini LLM to analyze each article for market sentiment (Positive/Neutral/Negative), classify it into a relevant financial category, and extract key entities like companies, people, and macroeconomic terms.
-   **Quantitative Scoring**: Provides a numeric score from -10.0 to +10.0 for each article, quantifying the potential market impact.
-   **Cost-Saving Test Mode**: Includes a test mode to run the full workflow with dummy data, allowing for development and testing without incurring any API costs.

---

## Setup and Configuration

Before running, you must provide API keys for the three external services this actor uses.

1.  **Google Programmable Search API**:
    * You need a **Google API Key** and a **Search Engine ID**.
    * Get your credentials from the [Google Cloud Console](https://console.cloud.google.com/).
2.  **Google AI Studio (Gemini API)**:
    * You need a **Gemini API Key**.
    * Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey).
3.  **Alpha Vantage API**:
    * You need an **Alpha Vantage API Key**.
    * Get your free key from the [Alpha Vantage website](https://www.alphavantage.co/support/#api-key).

### Add Keys to Apify Secrets

For security, add these keys as **secret environment variables** in your Apify Actor settings:

-   `GOOGLE_API_KEY`: Your Google API Key.
-   `GOOGLE_CSE_ID`: Your Programmable Search Engine ID.
-   `GEMINI_API_KEY`: Your Gemini API Key.
-   `ALPHA_VANTAGE_API`: Your Alpha Vantage API Key.

---

## Cost of Usage 💸

This actor incurs costs from four potential sources:

1.  **Apify Platform Usage**: Standard platform costs for the actor's runtime.
2.  **Google Programmable Search API**: Makes **one search query for every article** processed. The free tier includes 100 queries/day; paid usage is **$5 per 1,000 queries**.
3.  **Google AI Studio (Gemini API)**: This is a primary cost driver. It makes **two LLM calls for every article**: one for analysis and one for summarization (if enabled). Costs are based on token usage.
4.  **Alpha Vantage API**: Has a free tier of **25 requests per day**. If your actor runs exceed this limit, you may need a premium plan.

---

## Input

| Field            | Type    | Default | Description                                                                                             |
| ---------------- | ------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `source`         | String  | `all`   | The financial news category to use for both RSS and Alpha Vantage topics.                               |
| `customFeedUrl`  | String  | `null`  | A custom RSS feed URL to use if `source` is set to `custom`.                                            |
| `maxArticles`    | Integer | `10`    | The maximum number of articles to fetch from *each* source (RSS and Alpha Vantage).                     |
| `useSummarization`| Boolean | `true`  | If enabled, the actor will generate a Gemini summary for each article, incurring an additional LLM cost.|
| `runTestMode`    | Boolean | `false` | Bypasses all external API calls for zero-cost testing. **Do not enable in production.** |

---

## Output

The actor saves its results in the dataset. Each item is a structured JSON object with the following fields:

| Field          | Type           | Description                                                                    |
| -------------- | -------------- | ------------------------------------------------------------------------------ |
| `source`       | String         | The name of the news source (e.g., 'Financial Times (FT)', 'Alpha Vantage').   |
| `title`        | String         | The original title of the news article.                                        |
| `url`          | String         | The URL of the original article.                                               |
| `published`    | String         | The publication date string from the source.                                   |
| `summary`      | String         | The AI-generated summary of the article.                                       |
| `sentiment`    | String         | The AI-analyzed market sentiment (Positive, Neutral, Negative).                |
| `category`     | String         | The AI-assigned market category (e.g., 'Monetary Policy', 'Technology/FinTech').|
| `key_entities` | Array of Strings | A list of key companies, people, or macroeconomic terms mentioned.             |
| `gdelt_tone`   | Number         | A numeric score from -10.0 (very negative) to +10.0 (very positive).           |