# AI Content Opportunity Scout

## 🧠 What It Is

The `AI Content Opportunity Scout` is the second analysis stage, acting as the keyword and strategy expert in the ecosystem. It takes the trending topics identified by the `Topic Trend Aggregator` and enriches them with valuable SEO and keyword data.

Currently, this actor uses **mock data** to simulate calls to the Google Ads API, allowing for full pipeline testing without incurring API costs.

## ✨ Key Features

* **Keyword Enrichment**: For each topic, it simulates a Google Ads API call to fetch key metrics like average monthly search volume, competition level, and estimated top-of-page bid costs.
* **AI Cluster Score**: It calculates a proprietary `ai_cluster_score` (0-100) that synthesizes the topic's trend score, search volume, and competition level into a single, actionable metric. It also boosts the score for topics relevant to AI and technology.
* **Strategic Recommendation**: Based on the competition level and AI score, the actor determines the `best_strategy` for content creation, such as "Top Opportunity," "Niche Topic," or "High Competition, Worth the Investment."
* **Long-Tail Keyword Extraction**: It processes the key entities from the source articles to identify and analyze relevant long-tail keywords, providing deeper content opportunities.

## ⚙️ How It Works

1.  **Topic Ingestion**: The actor fetches the dataset of trending topics from the upstream `Topic Trend Aggregator`, filtering for topics that meet a minimum `trend_score`.
2.  **Concurrent Keyword Lookups**: It runs concurrent (mock) API calls for each high-priority topic to gather keyword metrics efficiently.
3.  **Scoring and Strategy Analysis**: For each topic, it merges the keyword data, calculates the `ai_cluster_score`, and determines the `best_strategy`.
4.  **Data Output**: The actor pushes the final, enriched data to its default dataset, making it available for the next stage in the pipeline, the `Sentiment Compass`.

## 📥 Inputs

* **`source_dataset_id`**: The ID of the dataset from the `Topic Trend Aggregator` to be used as input.
* **`min_trend_score`**: A threshold to filter out topics with low momentum.
* **`language_code`** and **`location_ids`**: Parameters to define the target language and region for the (mock) keyword metric lookups.
* **Secret API Keys**: While currently using mock data, the input schema is configured to securely accept all necessary API keys for a future live integration with Google Ads and OpenAI.

## 📤 Outputs

The actor enriches the incoming dataset, adding several key fields to each topic to provide a comprehensive strategic overview:

* **`search_volume`** (Integer): The estimated average monthly searches for the topic.
* **`competition`** (String): The competition level for the topic ("Low," "Medium," or "High").
* **`ai_cluster_score`** (Integer): The proprietary score indicating the overall opportunity.
* **`best_strategy`** (String): The AI-generated recommendation for how to approach content creation.
* **`long_tail_opportunities`** (Array): A list of related long-tail keywords with their own volume and competition data.