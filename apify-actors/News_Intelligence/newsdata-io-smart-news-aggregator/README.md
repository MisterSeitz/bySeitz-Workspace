# 📰 NewsData.io Smart News Aggregator

This Apify actor fetches and summarizes news articles from [NewsData.io](https://newsdata.io/) using configurable keywords, categories, and filters.  
It optionally uses **OpenAI** to generate concise summaries for each article, ideal for dashboards, research pipelines, and content monitoring workflows.

---

## 🚀 Features

- 🔍 **Search by Keywords** – Query topics like _oppression_, _corruption_, _justice_, or any custom combination.
- 🌍 **Filter by Country, Category, and Language** – Focus on specific regions or global results.
- ⚙️ **Domain Priority Control** – Use NewsData.io’s `prioritydomain` option to refine source quality.
- 🧠 **OpenAI Summarization** *(optional)* – Auto-summarize long descriptions into short readable summaries.
- 🧾 **Structured Output** – Stores clean JSON data in Apify datasets.
- 🧩 **Debug Mode** – Save raw API responses to the key-value store for troubleshooting or inspection.

---

## 🧩 Input Schema

| Field | Type | Description |
|-------|------|-------------|
| `keywords` | string | Comma-separated list of keywords (e.g., `oppression, corruption, injustice`). |
| `category` | select | One of: `business`, `crime`, `education`, `entertainment`, `health`, `science`, `sports`, `technology`, `world`. |
| `country` | select | Country code (e.g., `za`, `ng`, `us`, or `wo` for world). |
| `language` | select | `en`, `af`, or `zu`. |
| `domainOption` | select | Source domain filtering (e.g., `news24.com`, `iol.co.za`, `popular`, or `custom`). |
| `customDomain` | string | Specify a domain manually if `custom` selected. |
| `priorityDomain` | select | Domain quality preference: `top`, `medium`, or `low`. |
| `useOpenAI` | boolean | Enable summarization using OpenAI’s GPT model (requires `OPENAI_API_KEY`). |
| `maxArticles` | integer | Maximum number of articles to fetch. |
| `debugMode` | boolean | If true, saves raw API JSON to the key-value store for debugging. |

---

## 🔑 Environment Variables

| Variable | Description |
|-----------|-------------|
| `NEWSDATA_API_KEY` | Your [NewsData.io](https://newsdata.io/) API key. |
| `OPENAI_API_KEY` *(optional)* | OpenAI API key, required only if summarization is enabled. |

---

## 🧠 Example Input

```json
{
  "keywords": "oppression, corruption",
  "category": "world",
  "country": "za",
  "language": "en",
  "priorityDomain": "top",
  "useOpenAI": true,
  "maxArticles": 5,
  "debugMode": false
}