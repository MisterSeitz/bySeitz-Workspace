# 📰 GDELT Data Enrichment Pipeline

This Apify actor provides a powerful pipeline to query the [GDELT Project](https://www.gdeltproject.org/) for global news articles and enrich them with AI-powered analysis. It uses Google Search to gather context and OpenAI's models to generate summaries, extract sentiment, and identify key entities, turning raw news data into structured, actionable intelligence.

## ✨ Key Features

  * **Direct GDELT Querying**: Access the full power of the GDELT 2.0 DOC API with advanced query operators.
  * **AI-Powered Summarization**: Uses Google Search results to generate a concise, relevant summary of the core news event, avoiding the need to scrape the original article.
  * **In-Depth Analysis**: Automatically categorizes articles, determines risk/sentiment, and extracts key entities (companies, people, locations).
  * **Robust Date Extraction**: Intelligently finds the most accurate publication date, using GDELT's data first and falling back to a Google Search consensus if needed.
  * **Flexible Timeframes**: Fetch articles from a relative timespan (e.g., `1day`, `2weeks`) or an absolute date range.
  * **Pay-per-Value Monetization**: A fair pricing model where you only pay for the specific enrichment tasks you use.

## 🚀 Potential Use Cases

  * **Geopolitical Risk Monitoring**: Track news about specific regions, political figures, or themes like `(sanctions OR protest) AND country:ZA`.
  * **Market Intelligence**: Monitor financial news, company announcements, or economic trends with queries like `theme:ECON_STOCKMARKET AND "interest rates"`.
  * **Brand Reputation Tracking**: Keep an eye on news mentioning your brand, competitors, or key executives.
  * **Cybersecurity Threat Intelligence**: Identify reports of data breaches, vulnerabilities, or malware campaigns using queries like `(CVE-2025-XXXX OR "data breach")`.

## ⚙️ Input Configuration

The actor requires a GDELT query to start. Other fields are optional and allow you to customize the data retrieval.

| Field | Description | Example Value |
| :--- | :--- | :--- |
| **GDELT Search Query** | The GDELT query string. Use capitalized boolean operators (`AND`, `OR`). | `"Global Economy" OR theme:ECON_BUSINESS` |
| **Max GDELT Articles**| The maximum number of articles to retrieve from GDELT (up to 250). | `100` |
| **Time Range** | Specify a time span back from the present (e.g., '3days', '1week') or an absolute date range. | `3 days` |
| **Sort Results By** | The field to sort GDELT results by. "Relevance" is the default. | `Date (Newest First)` |
| **Source Language** | Filter results to a specific language (e.g., 'english' or 'EN'). | `english` |

## 📊 Output Data Structure

The actor outputs a dataset of enriched articles with the following structure:

| Field | Description |
| :--- | :--- |
| `source` | The domain name of the news source (e.g., `reuters.com`). |
| `title` | The original title of the article. |
| `url` | The direct URL to the original article. |
| `published` | The publication date in ISO 8601 format (e.g., `2025-10-16T14:30:00+00:00`). |
| `summary`| The AI-generated summary of the news event. |
| `sentiment` | The analyzed risk or impact level: `High Risk`, `Medium Risk`, or `Low Risk/Informational`. |
| `category` | The primary theme of the article (e.g., `Policy/Compliance`, `Threat Intelligence`). |
| `key_entities` | A list of up to 3 key companies, people, or vulnerabilities mentioned. |

### Example Output Item

```json
{
  "source": "turkiyegazetesi.com.tr",
  "title": "IMFden küresel ekonomi uyarısı !  Yavaşlama işaretlerini görmeye başlıyoruz",
  "url": "https://www.turkiyegazetesi.com.tr/ekonomi/imfden-kuresel-ekonomi-uyarisi-yavaslama-isaretlerini-gormeye-basliyoruz-1150130",
  "published": "2025-10-03T06:30:00+00:00",
  "summary": "The International Monetary Fund (IMF) has issued a global economic warning, stating that signs of slowdown are beginning to emerge...",
  "sentiment": "High Risk",
  "category": "Policy/Compliance",
  "key_entities": [
    "International Monetary Fund (IMF)",
    "Julie Kozack"
  ]
}
```

## 💰 Usage and Monetization

This actor uses a pay-per-value model. You are charged a small fee for each processing step, giving you full control over costs.

| Event Name | Title | Price Per Article |
| :--- | :--- | :--- |
| `gdelt-article-retrieved` | GDELT Article Retrieval | **$0.001** |
| `ai-summary-generated` | AI-Generated Summary | **$0.050** |
| `ai-in-depth-analysis` | In-Depth AI Analysis | **$0.010** |

**Total for one fully enriched article = $0.061**

## 🛠️ Setup and Configuration

To run this actor, you must configure the following **secret environment variables** in your Apify account (`Settings` \> `Secrets`):

  * `OPENAI_API_KEY`: Your OpenAI API key.
  * `GOOGLE_API_KEY`: Your Google Cloud API key with the "Custom Search API" enabled.
  * `GOOGLE_CSE_ID`: Your Google Programmable Search Engine ID.

These secrets are securely stored and automatically made available to the actor at runtime.