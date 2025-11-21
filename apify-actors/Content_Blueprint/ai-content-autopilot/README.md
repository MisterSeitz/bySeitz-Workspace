# AI Content Autopilot

## 🧠 What It Is

The `AI Content Autopilot` is the private, central coordinating brain of the entire AI Content Intelligence Ecosystem. Its primary role is to automate the full data pipeline, from fetching raw news to generating final content ideas. It manages data freshness, coordinates actor runs, and produces a final summary report.

This actor is the key to creating a "Continuous Intelligence" system that not only generates ideas but also builds a historical data asset over time.

## ⚙️ How It Works

The orchestrator runs a sequence of actors, managing the data flow between them. Here is the standard execution chain:

1.  **Data Ingestion**: Gathers articles from source pipelines (`global_markets`, `world_news`, etc.).
2.  **Aggregation**: Triggers `topic_trend_aggregator_actor` to find and score trending topics.
3.  **Keyword Analysis**: Triggers `keyword_opportunity_actor` to enrich topics with keyword data.
4.  **Sentiment Analysis**: Triggers `sentiment_intel_actor` to analyze the sentiment of each topic.
5.  **Idea Generation**: Finally, triggers the public `content_idea_generator_actor` to produce creative blueprints.

A key feature is its **caching logic**. Before running an actor, it checks when its last output dataset was created. If the data is recent enough (e.g., less than 6 hours old), it skips the run and reuses the existing data, saving time and compute units.

## 🚀 How to Schedule

This actor is designed for autonomous operation using the **Apify Scheduler**.

1.  Navigate to the actor's page in your Apify Console.
2.  Go to the "Schedules" tab.
3.  Create a new schedule.
4.  Set the schedule to run at a desired frequency, for example, every 6 or 12 hours (`0 */6 * * *`).
5.  Configure the input for the scheduled run, selecting the pipelines and stages you want to automate.

This setup ensures your content intelligence ecosystem is always up-to-date with the latest trends without any manual intervention.

## 🔒 Why It Must Remain Private

The `AI Content Autopilot` should **always be kept private**. It contains the core business logic of your entire content operation, including:

* **Internal API Keys & IDs**: It references the specific IDs of all other actors in the chain.
* **Orchestration Logic**: The sequence and rules for how your data is processed are proprietary.
* **Data Flow Management**: It has access to all intermediate datasets, which may contain sensitive or unprocessed information.
* **Security**: Exposing it publicly would allow anyone to trigger your entire pipeline, potentially leading to high usage costs and unauthorized access to your system's architecture.

This actor is the "brain" of your operation; protect it accordingly.