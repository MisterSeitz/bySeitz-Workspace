import os
import asyncio
import aiohttp
import json
from apify import Actor

def get_top_entities(topic_data: dict, max_entities: int) -> list:
    """Extracts and returns the top N entities based on mention counts."""
    all_entities = []
    entity_keys = [
        "mentioned_people", "mentioned_organizations", "mentioned_locations",
        "mentioned_products", "mentioned_events"
    ]
    
    for key in entity_keys:
        entities = topic_data.get(key, [])
        if isinstance(entities, list):
            for entity in entities:
                if isinstance(entity, dict) and 'name' in entity and 'mentions' in entity:
                    all_entities.append(entity)
    
    sorted_entities = sorted(all_entities, key=lambda x: x.get('mentions', 0), reverse=True)
    
    return [e['name'] for e in sorted_entities[:max_entities]]

async def analyze_sentiment_with_llm(session: aiohttp.ClientSession, topic: dict, max_entities_to_analyze: int, api_key: str) -> dict:
    """Calls an LLM to perform deep sentiment analysis on the topic and key entities."""
    
    articles = topic.get("articles", [])
    if not articles:
        return {}

    context = ". ".join([f"Title: {a.get('title', '')}. Summary: {a.get('summary', '')}" for a in articles[:10]])
    top_entities = get_top_entities(topic, max_entities_to_analyze)
    
    prompt = f"""
    Analyze the sentiment of the following news content. Provide a detailed JSON response.
    
    1.  **Overall Sentiment**: Analyze the overall sentiment of the text. Provide:
        -   `overall_sentiment_score`: A float from -1.0 to 1.0.
        -   `emotion_profile`: An object with scores for "fear", "optimism", "anger", "crisis", "hope", "opportunity".
        -   `volatility_score`: An integer from 0 to 100.
        -   `recommended_tone`: A brief, actionable recommendation.
        
    2.  **Entity-Specific Sentiment**: For each entity in the list below, determine their sentiment within this context.
        -   `entity_sentiments`: An array of objects, each with `name` and `sentiment` ("Positive", "Negative", or "Neutral").
        
    **List of Entities to Analyze**: {json.dumps(top_entities)}
    **News Content for Analysis**:
    ---
    {context[:8000]}
    ---
    Your response must be a single, valid JSON object.
    """
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}

    try:
        async with session.post(url, headers=headers, json=data) as response:
            response.raise_for_status()
            result = await response.json()
            content_str = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            return json.loads(content_str)
    except Exception as e:
        Actor.log.error(f"LLM analysis failed for topic '{topic.get('cluster_topic')}': {e}")
        return {}

def get_sentiment_label(score: float) -> str:
    """Converts a sentiment score to a string label."""
    if score > 0.1: return "Positive"
    elif score < -0.1: return "Negative"
    else: return "Neutral"

async def main():
    async with Actor:
        Actor.log.info("🚀 Starting Sentiment Compass...")
        
        actor_input = await Actor.get_input() or {}
        
        # API key is now retrieved only from the environment variable.
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            await Actor.fail("OPENAI_API_KEY environment variable is not set. This is required.")
            return
            
        source_dataset_id = actor_input.get("source_dataset_id")
        max_topics = actor_input.get("max_topics_to_process", 10)
        max_entities = actor_input.get("max_entities_to_analyze", 3)

        if not source_dataset_id:
            await Actor.fail("Input is missing 'source_dataset_id'. This is a required field.")
            return

        Actor.log.info(f"Fetching up to {max_topics} topics from dataset: {source_dataset_id}")
        
        try:
            dataset_client = Actor.apify_client.dataset(source_dataset_id)
            source_items = await dataset_client.list_items(limit=max_topics)
            topics_to_process = source_items.items
        except Exception as e:
            await Actor.fail(f"Could not read from source dataset {source_dataset_id}. Error: {e}")
            return
            
        Actor.log.info(f"Found {len(topics_to_process)} topics to analyze.")

        async with aiohttp.ClientSession() as session:
            tasks = [analyze_sentiment_with_llm(session, topic, max_entities, api_key) for topic in topics_to_process]
            analysis_results = await asyncio.gather(*tasks)

        final_output = []
        for original_topic, analysis in zip(topics_to_process, analysis_results):
            if not analysis:
                continue

            sentiment_score = analysis.get("overall_sentiment_score", 0.0)
            
            output_item = {
                "cluster_topic": original_topic.get("cluster_topic"),
                "trend_score": original_topic.get("trend_score"),
                "average_sentiment": get_sentiment_label(sentiment_score),
                "sentiment_score": sentiment_score,
                "emotion_profile": analysis.get("emotion_profile", {}),
                "volatility_score": analysis.get("volatility_score", 0),
                "recommended_tone": analysis.get("recommended_tone", "N/A"),
                "entity_sentiments": analysis.get("entity_sentiments", []),
                "source_cluster_id": original_topic.get("cluster_id"),
            }
            final_output.append(output_item)

        if final_output:
            await Actor.push_data(final_output)
            Actor.log.info(f"Successfully processed {len(final_output)} topics and saved to the dataset.")
        else:
            Actor.log.warning("No topics were successfully processed.")
            
        Actor.log.info("✅ Sentiment Compass finished successfully.")

if __name__ == "__main__":
    asyncio.run(main())