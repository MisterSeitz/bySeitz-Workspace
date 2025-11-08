import asyncio
from datetime import datetime, timezone
from apify import Actor

# A mapping of actor names to their Apify store IDs.
ACTOR_IDS = {
    "topic_trend_aggregator_actor": "byseitz.agency/topic-trend-aggregator",
    "keyword_opportunity_actor": "byseitz.agency/ai-content-opportunity-scout",
    "sentiment_intel_actor": "byseitz.agency/sentiment-compass-ai-powered",
    "content_idea_generator_actor": "byseitz.agency/content-blueprint-ai",
}

# This mapping provides the full input object required by the topic-trend-aggregator.
PIPELINE_MAPPING = {
    "global_markets": {
        "actorId": "iRfe4oocMnOpxGtAm",
        "categoryName": "Global Markets Intelligence",
        "sourceType": "Verified News"
    },
    "world_news": {
        "actorId": "apify/google-news-scraper",
        "categoryName": "World News Updates",
        "sourceType": "Verified News"
    },
    "artificial_intelligence": {
        "actorId": "WwB1ORDfMlK9SAVih",
        "categoryName": "Artificial Intelligence Sector",
        "sourceType": "Verified News"
    },
    "venture_capital": {
        "actorId": "dan.qa/venture-capital-news",
        "categoryName": "Venture Capital Funding",
        "sourceType": "Blog Feed"
    },
    "global_geopolitical_news": {
        "actorId": "byseitz.agency/gdelt-news",
        "categoryName": "Global Geopolitical & Economic News",
        "sourceType": "Verified News"
    }
}

def get_dataset_url(dataset_id: str) -> str:
    """Constructs the URL for a given dataset ID."""
    return f"https://console.apify.com/storage/datasets/{dataset_id}"

async def main():
    """
    Main function for the AI Content Autopilot.
    """
    async with Actor:
        Actor.log.info("Starting the AI Content Autopilot...")

        # Get and validate actor input
        actor_input = await Actor.get_input() or {}
        openai_api_key = actor_input.get("openaiApiKey")
        pipelines = actor_input.get("pipelinesToInclude", [])
        
        run_aggregator = actor_input.get("runAggregator", True)
        run_keyword_analysis = actor_input.get("runKeywordAnalysis", True)
        run_sentiment_analysis = actor_input.get("runSentimentAnalysis", True)
        run_idea_generation = actor_input.get("runIdeaGeneration", True)
        
        output_formats = actor_input.get("outputFormats", [])

        if not pipelines:
            await Actor.fail("No pipelines selected. Please specify at least one pipeline to include.")
            return

        if not openai_api_key:
            await Actor.fail("OpenAI API Key is missing. Please provide it in the input.")
            return

        run_id = Actor.get_env().get('APIFY_ACTOR_RUN_ID')
        start_time = datetime.now(timezone.utc)
        
        final_datasets = {}
        
        # --- Stage 1: Topic Trend Aggregation ---
        aggregator_dataset_id = None
        if run_aggregator:
            Actor.log.info("--- Stage 1: Topic Trend Aggregation ---")
            
            news_sources_input = [PIPELINE_MAPPING[p] for p in pipelines if p in PIPELINE_MAPPING]

            if not news_sources_input:
                await Actor.fail("The selected pipelines are not valid. Please check the input configuration.")
                return

            aggregator_input = {
                "news_sources": news_sources_input,
                "max_articles": 25,
                "max_clusters_per_category": 5
            }
            
            Actor.log.info("Running Topic Trend Aggregator...")
            run_info = await Actor.call(
                ACTOR_IDS["topic_trend_aggregator_actor"],
                run_input=aggregator_input
            )
            # FIX: Access the attribute directly instead of using .get()
            aggregator_dataset_id = run_info.default_dataset_id
            if not aggregator_dataset_id:
                await Actor.fail("Topic Trend Aggregator did not produce an output dataset.")
                return
            
            final_datasets["aggregator"] = get_dataset_url(aggregator_dataset_id)
            Actor.log.info(f"Topic Trend Aggregator finished. Output dataset: {aggregator_dataset_id}")
        else:
            Actor.log.info("Skipping Stage 1: Topic Trend Aggregation.")

        # --- Stage 2: Keyword Opportunity Analysis ---
        keyword_dataset_id = None
        if run_keyword_analysis:
            if not aggregator_dataset_id:
                Actor.log.warning("Skipping Keyword Analysis because the aggregator stage did not run or failed.")
            else:
                Actor.log.info("--- Stage 2: Keyword Opportunity Analysis ---")
                keyword_input = { "source_dataset_id": aggregator_dataset_id }
                Actor.log.info("Running Keyword Opportunity Actor...")
                run_info = await Actor.call(ACTOR_IDS["keyword_opportunity_actor"], run_input=keyword_input)
                # FIX: Access the attribute directly instead of using .get()
                keyword_dataset_id = run_info.default_dataset_id
                if not keyword_dataset_id:
                    await Actor.fail("Keyword Opportunity Actor did not produce an output dataset.")
                    return

                final_datasets["keyword_opportunity"] = get_dataset_url(keyword_dataset_id)
                Actor.log.info(f"Keyword Opportunity Actor finished. Output dataset: {keyword_dataset_id}")
        else:
            Actor.log.info("Skipping Stage 2: Keyword Opportunity Analysis.")
        
        sentiment_input_dataset_id = keyword_dataset_id or aggregator_dataset_id

        # --- Stage 3: Sentiment Intel Analysis ---
        sentiment_dataset_id = None
        if run_sentiment_analysis:
            if not sentiment_input_dataset_id:
                Actor.log.warning("Skipping Sentiment Analysis because no previous stage produced a dataset.")
            else:
                Actor.log.info("--- Stage 3: Sentiment Intel Analysis ---")
                sentiment_input = { "source_dataset_id": sentiment_input_dataset_id }
                Actor.log.info("Running Sentiment Intel Actor...")
                run_info = await Actor.call(ACTOR_IDS["sentiment_intel_actor"], run_input=sentiment_input)
                # FIX: Access the attribute directly instead of using .get()
                sentiment_dataset_id = run_info.default_dataset_id
                if not sentiment_dataset_id:
                    await Actor.fail("Sentiment Intel Actor did not produce an output dataset.")
                    return

                final_datasets["sentiment_intel"] = get_dataset_url(sentiment_dataset_id)
                Actor.log.info(f"Sentiment Intel Actor finished. Output dataset: {sentiment_dataset_id}")
        else:
            Actor.log.info("Skipping Stage 3: Sentiment Intel Analysis.")
            
        content_gen_input_dataset_id = sentiment_dataset_id or sentiment_input_dataset_id

        # --- Stage 4: Content Idea Generation ---
        content_dataset_id = None
        if run_idea_generation:
            if not content_gen_input_dataset_id:
                 Actor.log.warning("Skipping Content Idea Generation because no previous stage produced a dataset.")
            else:
                Actor.log.info(f"Cleaning dataset {content_gen_input_dataset_id} before final stage.")
                
                dataset_client = Actor.apify_client.dataset(content_gen_input_dataset_id)
                items_list = await dataset_client.list_items()
                
                cleaned_items = []
                for item in items_list.items:
                    topic = item.get("cluster_topic", "")
                    articles = item.get("articles", [])
                    if topic and "untitled" not in topic.lower() and articles:
                        cleaned_items.append(item)

                if not cleaned_items:
                    Actor.log.warning("No valid topics with articles found after cleaning. Skipping final stage.")
                else:
                    cleaned_dataset_client = await Actor.apify_client.datasets().get_or_create(name="cleaned-input-for-content-gen")
                    await cleaned_dataset_client.push_items(cleaned_items)
                    
                    Actor.log.info("--- Stage 4: Content Idea Generation ---")
                    content_input = {
                        "dataset_id": cleaned_dataset_client.id,
                        "output_formats": output_formats,
                    }
                    Actor.log.info("Running Content Idea Generator with cleaned data...")
                    run_info = await Actor.call(ACTOR_IDS["content_idea_generator_actor"], run_input=content_input)
                    # FIX: Access the attribute directly instead of using .get()
                    content_dataset_id = run_info.default_dataset_id
                    if not content_dataset_id:
                        await Actor.fail("Content Idea Generator did not produce an output dataset.")
                        return

                    final_datasets["content_idea_generator"] = get_dataset_url(content_dataset_id)
                    Actor.log.info(f"Content Idea Generator finished. Output dataset: {content_dataset_id}")
        else:
            Actor.log.info("Skipping Stage 4: Content Idea Generation.")

        # --- Final Step: Generate Summary Report ---
        Actor.log.info("--- Generating Final Summary Report ---")
        
        topics_found, content_items_generated = 0, 0
        if aggregator_dataset_id:
            try:
                dataset_info = await Actor.apify_client.dataset(aggregator_dataset_id).get()
                topics_found = dataset_info.get("itemCount", 0) if dataset_info else 0
            except Exception as e:
                Actor.log.warning(f"Could not retrieve stats from aggregator dataset: {e}")

        if content_dataset_id:
            try:
                dataset_info = await Actor.apify_client.dataset(content_dataset_id).get()
                content_items_generated = dataset_info.get("itemCount", 0) if dataset_info else 0
            except Exception as e:
                Actor.log.warning(f"Could not retrieve stats from content ideas dataset: {e}")

        summary_report = {
            "run_id": f"{start_time.strftime('%Y-%m-%dT%H-%M-%SZ')}-{run_id}",
            "status": "Completed",
            "pipelines_used": pipelines,
            "topics_found": topics_found,
            "content_items_generated": content_items_generated,
            "datasets": final_datasets,
        }

        await Actor.push_data([summary_report])
        Actor.log.info("Orchestration complete. Summary report generated.")

if __name__ == "__main__":
    asyncio.run(main())