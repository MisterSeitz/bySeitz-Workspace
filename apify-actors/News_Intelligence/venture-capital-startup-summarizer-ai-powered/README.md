# 💸 Venture Capital Intelligence Pipeline (AI Powered)

This Apify Actor processes Venture Capital and Tech funding news from major RSS feeds and transforms headlines into structured, actionable intelligence using the Google Search Results Scraper's AI Overview and combined Language Model (LLM) analysis.

This pipeline replaces unreliable traditional web scraping (Playwright/Trafilatura) with a robust, two-stage AI analysis approach, ensuring high data uniformity and value for VC professionals, investors, and analysts.

***

## ✨ New Functionality and Value Proposition

The actor now delivers reliable, structured data by **pivoting entirely away from content scraping** and towards intelligent aggregation and analysis.

| Feature | New Method (AI Pipeline) | Value to End-User |
| :--- | :--- | :--- |
| **Data Reliability** | **Highly reliable** via Apify's managed Google Search Scraper. | Guaranteed, uniform summary data, bypassing paywalls. |
| **Core Summary** | **AI Overview** from Google Search, providing a concise, aggregated summary. | High-quality, standardized news digest. |
| **Sentiment Analysis** | **Added:** Sentiment label (`Positive`, `Neutral`, `Negative`). | Quick assessment of the market/investor mood toward the news. |
| **Categorization** | **Added:** Primary market topic (`Funding Round`, `Acquisition/Exit`, `Venture Strategy`, etc.). | Easy data filtering for deal flow, trend spotting, and competitive analysis. |
| **Key Entities** | **Added:** List of 1-3 major companies, investors, or founders. | Enables immediate linking of news to specific startups or VC firms. |

***

## ⚙️ How the Pipeline Works

The workflow is managed by LangGraph and consists of three robust steps:

1.  **RSS Fetcher:** Collects and deduplicates articles from specified VC RSS feeds (TechCrunch, Crunchbase, Forbes VC, etc.).
2.  **Google Search AI Summary (Pay Point 1):** Uses the article title as a query input for the `apify/google-search-results` Actor with the `aiModeOnly` setting enabled. This reliably extracts the AI Overview, which serves as the article's core summary.
3.  **Combined LLM Analysis (Pay Point 2):** The AI Overview text is passed to a single, structured LLM call (e.g., GPT-3.5-turbo). This call simultaneously performs Sentiment Analysis, Categorization, and Key Entity Extraction, returning all analytical data in one efficient JSON object.

***

## 💰 Cost Structure (2 Pay Points per Article)

The cost structure is based on two separate, valuable service calls for every successfully processed article:

| Pay Point | Service | Event Name | Purpose |
| :--- | :--- | :--- | :--- |
| **1 (Search)** | Google Search Results Scraper | `article-fetch` | Covers the cost of running the Google Search Actor and acquiring the AI Overview. |
| **2 (Analysis)** | OpenAI/External LLM | `llm-analysis-tokens-used` | Covers the token cost for the single, combined LLM request that generates the sentiment, category, and entities. |

***

## 📥 Output Dataset Schema (`DatasetRecord`)

The final output is a structured JSON object pushed to the Apify dataset, containing only the high-value data points:

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `source` | string | Source of the article (e.g., TechCrunch). |
| `title` | string | Headline of the article. |
| `url` | string | Full URL of the original article. |
| `published` | string (Optional) | Date and time the article was published. |
| `summary` | string (Optional) | **AI Overview summary** retrieved from Google Search. |
| `sentiment` | string (Optional) | **Sentiment label:** `Positive`, `Neutral`, `Negative`, or `N/A`. |
| `category` | string (Optional) | **Primary VC topic:** (e.g., `Funding Round`, `Acquisition/Exit`). |
| `key_entities` | array of strings (Optional) | **Key entities:** List of up to 3 major companies/investors mentioned. |