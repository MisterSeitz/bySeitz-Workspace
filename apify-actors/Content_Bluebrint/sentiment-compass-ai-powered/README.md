# Sentiment Compass

## 🧠 What It Is

The `Sentiment Compass` is the third and most nuanced analysis stage in the AI Content Intelligence Ecosystem. It functions as a powerful **hybrid controller**, capable of either orchestrating the upstream news and keyword pipelines (Mode A) or analyzing a pre-existing dataset (Mode B). Its primary role is to add a deep layer of emotional and perceptual context to trending topics, moving beyond simple positive/negative labels to create a full emotional profile.

## ✨ Key Features

* **Hybrid Operational Modes**: Can run as a full-pipeline orchestrator or as a standalone analysis tool on a specific dataset ID or raw JSON input, providing maximum flexibility.

* **Advanced Emotional Profiling**: Instead of just a single sentiment score, the actor uses an LLM to generate a detailed `emotion_profile` (measuring fear, optimism, anger, crisis, hope, and opportunity) and a `volatility_score` to gauge how polarized the topic is.

* **Strategic Tone Recommendation**: Based on the combined sentiment, emotion, and volatility data, the actor provides a `recommended_tone` for content creation (e.g., "Enthusiastic and Visionary," "Balanced and Contextual"), guiding creators on how to approach sensitive or opportunistic topics.

* **Mock Data for Testing**: Includes a test mode that uses hardcoded dummy data, allowing for zero-cost testing of the analysis logic without making live API calls.

## ⚙️ How It Works

1. **Determine Data Source**: The actor first checks its input to decide which mode to operate in.

   * **Mode A (Orchestration)**: If a `newsSourceSelector` is provided, it triggers the upstream `Topic Trend Aggregator` and `AI Opportunity Scout` actors in sequence, waiting for them to complete and using their final output.

   * **Mode B (Direct Feed)**: If a `sourceDatasetId` or `rawJsonTopics` input is provided, it skips orchestration and loads the data directly.

2. **Text Extraction**: For each topic, it intelligently extracts all relevant text for analysis from the topic name and its associated long-tail keywords.

3. **LLM Analysis**: It sends this consolidated text to an LLM (e.g., `gpt-4o-mini`) to perform the comprehensive sentiment and emotional analysis.

4. **Data Enrichment & Output**: The actor processes the LLM's response, calculates the final metrics, and enriches the original topic data with the new sentiment-related fields before pushing the final, fully analyzed result to its output dataset.

## 📥 Inputs

* **`openaiApiKey` (Secret)**: Your OpenAI API Key is required for the core sentiment and emotion analysis.

* **`topicsToAnalyze`**: Limits how many topics are processed in a single run.

* **`sentimentModel`**: Allows you to select the AI model for analysis.

* **Mode A/B Fields**: Specific inputs like `newsSourceSelector` or `sourceDatasetId` to control the operational mode.

## 📤 Outputs

The actor produces a final, fully enriched dataset ready for the `Content Blueprint AI`. Each row represents a topic and contains all the data from the previous stages, plus the following key additions:

* **`average_sentiment`** (String): The overall sentiment classification ("Positive," "Negative," or "Neutral").

* **`emotion_profile`** (Object): A dictionary of key emotions and their corresponding scores (e.g., `{"fear": 0.8, "optimism": 0.1}`).

* **`volatility_score`** (Integer): A score from 0 to 100 indicating the degree of controversy or polarization surrounding the topic.

* **`recommended_tone`** (String): A clear, actionable recommendation for the tone and style of content that should be created for this topic.