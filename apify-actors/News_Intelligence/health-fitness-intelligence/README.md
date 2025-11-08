# 🥗 Health & Fitness Intelligence Pipeline

This actor is a powerful data-gathering tool that transforms raw news from top RSS feeds (focused on Health, Fitness, and Nutrition) into structured, actionable intelligence. It uses **DuckDuckGo News Search** to gather real-time context and an LLM (OpenAI) to perform advanced analysis.

The structured data it produces is intended for consumption by downstream systems, such as our flagship actor, **Content Blueprint AI**, which can use this stream of data to generate social posts, health guides, blog content, and more.

---

## How to Use

The primary function of this actor is to transform raw RSS headlines into highly analyzed, structured data.

1.  **As a Standalone Tool:** Run this actor to generate high-quality, structured news intelligence. You can download the resulting dataset for your own trend analysis, reports, or to feed into other custom workflows.
2.  **As a Data Source for Downstream Systems:** Run this actor on a schedule to build a dataset of fresh intelligence. Other tools, including the `Content Blueprint AI` actor, can then be pointed to this actor's dataset to generate final content.

---

## Features

-   **Comprehensive Source Aggregation**: Gathers news from a curated list of top-tier Health, Fitness, and Nutrition RSS feeds.
-   **Real-Time Grounding (DuckDuckGo Priority)**: For every article, the pipeline executes a targeted **DuckDuckGo News Search** to retrieve fresh, corroborating snippets. This ensures the synthesis is based on current, cross-validated information, overriding the often brief or delayed content of raw RSS summaries.
-   **Advanced AI Analysis**: Leverages an LLM to analyze each article for importance/sentiment (e.g., `High Importance`, `General Info/Tip`), categorize the topic (e.g., `Nutrition/Recipes`, `Medical News/Research`), and extract key entities.
-   **Resilient Processing**: The pipeline is designed to **fall back** to the original RSS summary if the DuckDuckGo search fails, ensuring the run completes without crashing and successfully processing all possible articles.
-   **Duplicate Prevention**: Intelligently tracks processed articles across runs to ensure you only process and pay for new information.
-   **Cost-Saving Test Mode**: Includes a test mode to run the full workflow with dummy data, allowing for development and testing without incurring API costs.

---

## Setup and Configuration

Before running the actor, you only need to provide an API key for the LLM service.

1.  **OpenAI API Key**:
    * You will need an API key from your OpenAI account.

### Add Keys to Apify Secrets

For security, add this key as a **secret environment variable** in your Apify Actor settings:

-   `OPENAI_API_KEY`: Your OpenAI API Key.

---

## Cost of Usage 💸

**Important Note:** The costs listed below are for **this actor only**.

### Costs for This Actor

1.  **Apify Platform Usage**: Standard platform costs for running the actor.
2.  **DuckDuckGo Search**: This service is **free** and is handled internally by the actor, replacing the need for paid search APIs. The actor performs **one search query for every article** it processes.
3.  **OpenAI API**: This is the primary cost. The actor makes **two LLM calls for every article**: one to summarize the DuckDuckGo Search snippets and another to perform the final structured analysis (importance, category, etc.). The total consumption is tracked via a dedicated usage event.

---

## Input

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `source` | String | `all` | The news source category to use (e.g., 'all', 'precision-nutrition'). |
| `customFeedUrl` | String | `null` | A custom RSS feed URL to use if `source` is set to `custom`. |
| `maxArticles` | Integer | `20` | The maximum number of new articles to fetch and process in a single run. |
| `region` | String | `wt-wt` | Region to limit DuckDuckGo search results by (e.g., 'us-en' for US, 'wt-wt' for World). |
| `timeLimit` | String | `w` | Limit DuckDuckGo search results by time ('d' for day, 'w' for week). |
| `runTestMode` | Boolean | `false` | Bypasses all external API calls for zero-cost testing. **Do not enable in production.** |

---

## Output

The actor saves its results in the dataset. Each item is a structured JSON object:

| Field | Type | Description |
| :--- | :--- | :--- |
| `source` | String | The name of the news source (e.g., 'Precision Nutrition'). |
| `title` | String | The original title of the news article. |
| `url` | String | The URL of the original article. |
| `published` | String | The publication date string from the RSS feed. |
| `summary` | String | The AI-generated summary of the article content. |
| `sentiment` | String | The AI-analyzed importance/impact (e.g., `High Importance`, `General Info/Tip`). |
| `category` | String | The AI-assigned category (e.g., `Nutrition/Recipes`, `General Fitness/Training`). |
| `key_entities` | Array of Strings | A list of key ingredients, exercises, health concepts, or brands. |