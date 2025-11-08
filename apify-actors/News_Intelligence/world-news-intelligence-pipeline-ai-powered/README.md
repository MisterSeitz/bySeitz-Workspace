# 🌎 World News Intelligence Pipeline (AI Powered)

This Apify Actor processes general world news from major RSS feeds and transforms headlines into structured, actionable intelligence using the Google Search Results Scraper's AI Overview and combined Language Model (LLM) analysis. This pipeline prioritizes source diversity by cycling through feeds within a selected category, ensuring broad coverage.

***

## ✨ New Functionality and Value Proposition

The pipeline now delivers uniform, structured data by **pivoting entirely away from content scraping** and towards intelligent aggregation and analysis.

| Feature | New Metric/Value | Value to End-User |
| :--- | :--- | :--- |
| **Source Diversity** | **Guaranteed Round-Robin** fetching from multiple sources within a selected category (e.g., *World/Politics*). | Ensures broad perspective and minimizes reliance on a single news outlet. |
| **Core Summary** | **AI Overview** from Google Search. | High-quality, standardized news digest, bypassing paywalls. |
| **Sentiment Analysis** | **Sentiment Label** (`Positive`, `Neutral`, `Negative`). | Quick assessment of the overall tone regarding the event. |
| **Categorization** | **Primary Category:** (`Politics/Government`, `Conflict/Security`, `Economy/Trade`, etc.). | Easy data filtering to track specific global events and themes. |
| **Key Entities** | **Key Entities:** Countries, Organizations (UN, NATO), or Individuals. | Enables immediate tracking of major global actors and regions. |

***

## ⚙️ How the Pipeline Works

The workflow is managed by LangGraph and consists of three robust steps:

1.  **RSS Fetcher:** Collects articles based on a chosen category (e.g., *Health/Science*). It ensures the first articles fetched come from different sources within that category until all sources are exhausted.
2.  **Google Search AI Summary (Pay Point 1):** Calls the `apify/google-search-results` Actor to reliably extract the AI Overview, which serves as the article's core summary.
3.  **Combined LLM Analysis (Pay Point 2):** The AI Overview is sent to a single LLM call (e.g., GPT-3.5-turbo). This call simultaneously assesses **Sentiment**, assigns a **Thematic Category**, and extracts **Key Entities**.

***

## 💰 Cost Structure (2 Pay Points per Article)

The cost structure is based on two separate, valuable service calls for every successfully processed article:

| Pay Point | Service | Event Name | Purpose |
| :--- | :--- | :--- | :--- |
| **1 (Search)** | Google Search Results Scraper | `article-fetch` | Covers the cost of running the Google Search Actor and acquiring the AI Overview. |
| **2 (Analysis)** | OpenAI/External LLM | `llm-analysis-tokens-used` | Covers the token cost for the single, combined LLM request that generates the analysis. |

***

## 🔧 Prerequisites

* **Apify API Token:** Must be configured as an environment variable (`APIFY_TOKEN`).
* **OpenAI API Key:** Must be configured as an environment variable (`OPENAI_API_KEY`).

***

## 4. `Dockerfile` & `requirements.txt`

These files should be identical to the clean, minimal versions used for all other pipelines.

### 🐳 `Dockerfile`

```dockerfile
# First, specify the base Docker image.
FROM apify/actor-python:3.13

# Second, copy just requirements.txt into the Actor image.
COPY --chown=myuser:myuser requirements.txt ./

# 💡 FIX: Install dependencies directly to bypass the requirements.txt newline error.
RUN PACKAGES="apify apify-client pydantic langgraph feedparser openai" \
    && echo "Python version:" \
    && python --version \
    && echo "Pip version:" \
    && pip --version \
    && echo "Installing dependencies:" \
    && pip install $PACKAGES \
    && echo "All installed Python packages:" \
    && pip freeze

# Next, copy the remaining files and directories with the source code.
COPY --chown=myuser:myuser . ./

# Use compileall to ensure the runnability of the Actor Python code.
RUN python3 -m compileall -q src/

# Specify how to launch the source code of your Actor.
CMD ["python3", "-m", "src"]