import os
import json
import asyncio
import logging
from typing import Any, Dict

import aiohttp
from apify import Actor
from apify_client import ApifyClient
from apify_client.errors import ApifyApiError
from tenacity import retry, stop_after_attempt, wait_exponential

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# --- Source to Actor ID Mapping ---
SOURCE_TO_ACTOR_MAP = {
    "Global Markets Intelligence": "iRfe4oocMnOpxGtAm",
    "Artificial Intelligence Sector": "WwB1ORDfMlK9SAVih",
    # Add other actor IDs here as needed
}

# -------------------------------------------------------------------
# ASYNC LLM CALL HANDLER (REWRITTEN FOR ROBUSTNESS)
# -------------------------------------------------------------------
async def generate_llm_response(session: aiohttp.ClientSession, prompt: str, temperature: float = 0.7) -> Dict:
    """Async call to OpenAI API with robust error handling and logging."""
    url = "https://api.openai.com/v1/chat/completions"
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        log.error("CRITICAL: OPENAI_API_KEY environment variable is not set.")
        # In a real scenario, this might call Actor.fail()
        return {}
    
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    
    try:
        async with session.post(url, headers=headers, json=data) as resp:
            resp.raise_for_status() # Raise an exception for bad status codes
            result = await resp.json()
            
            if not result.get("choices"):
                log.error(f"LLM API returned no 'choices'. Full response: {result}")
                return {}

            content_str = result["choices"][0].get("message", {}).get("content")
            if not content_str:
                log.warning("LLM response content was empty.")
                return {}

            return json.loads(content_str)

    except aiohttp.ClientError as e:
        log.error(f"HTTP Client Error during LLM call: {e}")
        return {}
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse JSON from LLM. Raw text: '{content_str}'. Error: {e}")
        return {}
    except Exception as e:
        log.error(f"An unexpected error occurred in generate_llm_response: {e}")
        return {}

# -------------------------------------------------------------------
# Refactored Actor Call with Retry to use the Actor's client
# -------------------------------------------------------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
async def call_actor_with_retry(actor_id: str, input_data: dict) -> Any:
    """Calls an upstream actor using the main Actor's client."""
    log.info(f"Calling upstream actor: {actor_id}")
    
    # Use the initialized ApifyClient instance directly to avoid potential proxy issues with the decorator
    client: ApifyClient = Actor.apify_client
    run = await client.actor(actor_id).call(run_input=input_data)
    
    if not run or 'status' not in run:
        log.error(f"Calling upstream actor {actor_id} failed to return a valid run object. Response: {run}")
        raise RuntimeError(f"Upstream actor {actor_id} did not return a valid run object.")
    
    log.info(f"Upstream actor {actor_id} finished with status: {run.get('status')}")
    if run.get("status") != "SUCCEEDED":
        raise RuntimeError(f"Upstream actor {actor_id} did not succeed. Run details: {run}")
    return run

async def generate_content_for_topic(session: aiohttp.ClientSession, topic: dict, temperature: float) -> Dict[str, Any]:
    topic_name = topic.get("cluster_topic", "Untitled")
    tone = topic.get("final_generation_tone", "Informative")
    trend_score = topic.get("trend_score", 0)
    log.info(f"Generating content for topic: {topic_name} with tone: {tone}")
    
    prompts = {
        "tiktok_script": f"Write a TikTok teleprompter script about '{topic_name}' in a {tone} tone. Respond ONLY with a valid JSON object with keys: 'hook', 'body_script', 'visual_cues', 'call_to_action'.",
        "youtube_video": f"Write a detailed YouTube video script outline about '{topic_name}' in a {tone} tone. Respond ONLY with a valid JSON object with keys: 'title', 'hook', 'introduction', 'main_point_1', 'main_point_2', 'call_to_action'.",
        "blog_article": f"Write a comprehensive blog article outline about '{topic_name}' in a {tone} tone. Respond ONLY with a valid JSON object with keys: 'title', 'introduction', 'section_1', 'section_2', 'section_3', 'conclusion'."
    }
    
    tasks = {fmt: asyncio.create_task(generate_llm_response(session, prompt, temperature)) for fmt, prompt in prompts.items()}
    results = {fmt: await task for fmt, task in tasks.items()}
    
    return {
        "topic": topic_name, "trend_score": trend_score, "final_generation_tone": tone,
        "content_outputs": {
            "tiktok_script": results.get("tiktok_script"),
            "youtube_video": results.get("youtube_video"),
            "blog_outline": results.get("blog_article") # Fixed key to match prompt
        }
    }

# -------------------------------------------------------------------
# MAIN ACTOR ENTRYPOINT
# -------------------------------------------------------------------
async def main() -> None:
    async with Actor:
        Actor.log.info("Initializing Content Blueprint AI Actor...")
        input_data = await Actor.get_input() or {}
        mode = input_data.get("input_source", "DatasetID")
        items = []

        if mode == "Orchestration":
            Actor.log.info("Running in Orchestration Mode...")
            initial_pipeline_source = input_data.get("initial_pipeline_source")
            actor_id_to_call = SOURCE_TO_ACTOR_MAP.get(initial_pipeline_source)
            if not actor_id_to_call:
                await Actor.fail(status_message=f"No actor ID mapped for source: {initial_pipeline_source}")
                return
            
            aggregator_input = {"news_sources": [{"actorId": actor_id_to_call, "categoryName": initial_pipeline_source}]}
            try:
                # Note: call_actor_with_retry is now async
                aggregator_run = await call_actor_with_retry("byseitz.agency/topic-trend-aggregator", aggregator_input)
                dataset_id = aggregator_run.get("defaultDatasetId")
                if dataset_id:
                    Actor.log.info(f"Orchestration complete. Fetching from Dataset ID: {dataset_id}")
                    # Use the Actor's client to interact with the dataset
                    dataset_client = Actor.apify_client.dataset(dataset_id)
                    list_items_response = await dataset_client.list_items(limit=input_data.get("max_topics", 10))
                    items = list_items_response.items
                else:
                    await Actor.fail(status_message="Upstream actor did not return a dataset ID.")
                    return
            except Exception as e:
                await Actor.fail(status_message=f"Orchestration failed: {e}")
                return

        elif mode == "DatasetID":
            dataset_id = input_data.get("dataset_id")
            if not dataset_id:
                await Actor.fail(status_message="`dataset_id` is required in DatasetID mode.")
                return
            Actor.log.info(f"Fetching data from Dataset ID: {dataset_id}")
            dataset_client = Actor.apify_client.dataset(dataset_id)
            list_items_response = await dataset_client.list_items(limit=input_data.get("max_topics", 10))
            items = list_items_response.items
        
        if not items:
            Actor.log.warning("No topics found to process. Exiting.")
            return

        Actor.log.info(f"Processing {len(items)} topics...")
        temperature = input_data.get("creativity_level", 70) / 100
        async with aiohttp.ClientSession() as session:
            tasks = [generate_content_for_topic(session, topic, temperature) for topic in items]
            results = await asyncio.gather(*tasks)

        # *** MODIFICATION: Open only the default dataset to store all results. ***
        default_ds = await Actor.open_dataset()

        push_tasks = []
        for res in results:
            # *** MODIFICATION: Push the entire result object for each topic to the default dataset. ***
            # This object contains the topic info and all its generated content blueprints.
            push_tasks.append(default_ds.push_data(res))

        if push_tasks:
            Actor.log.info(f"Pushing {len(push_tasks)} items to the default dataset...")
            await asyncio.gather(*push_tasks)
            Actor.log.info("All push operations have completed.")
        else:
            Actor.log.warning("No valid content was generated to be pushed.")

        Actor.log.info("Actor finished successfully.")

# This part remains the same
# if __name__ == "__main__":
#     asyncio.run(main())