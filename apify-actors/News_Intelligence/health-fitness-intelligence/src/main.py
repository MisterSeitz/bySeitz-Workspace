import os
from apify import Actor
from langgraph.graph import StateGraph
from typing import List, TypedDict
import asyncio
import hashlib
import re # Added for HTML stripping helper function
from .models import RSSFeed, Article, InputConfig, DatasetRecord
from .tools import fetch_rss_feeds, fetch_summary_from_duckduckgo, analyze_article_summary
from apify.storages import KeyValueStore

# --- HELPER FUNCTION FOR CLEANING (ADDED) ---
def strip_html_tags(text):
    """Removes HTML tags and cleans up extra whitespace."""
    if not text:
        return ""
    # Remove HTML tags (simple regex)
    clean = re.sub('<[^<]+?>', '', text)
    # Remove excessive whitespace
    clean = ' '.join(clean.split())
    return clean
# --------------------------------------------

class WorkflowState(TypedDict):
    config: InputConfig
    articles: List[Article]
    processed_count: int
    processed_urls_store: KeyValueStore

async def rss_fetcher(state: WorkflowState) -> dict:
    config = state["config"]
    processed_urls_store = state["processed_urls_store"]

    all_articles_from_feed = fetch_rss_feeds(
        config.source,
        custom_url=config.customFeedUrl,
        max_articles=config.maxArticles
    )

    new_articles = []
    Actor.log.info(f"Fetched {len(all_articles_from_feed)} total articles. Checking for duplicates...")

    for article in all_articles_from_feed:
        url_key = hashlib.md5(str(article.link).encode('utf-8')).hexdigest()
        is_duplicate = await processed_urls_store.get_value(url_key)
        if not is_duplicate:
            new_articles.append(article)

    if len(new_articles) < config.maxArticles:
        needed = config.maxArticles - len(new_articles)
        Actor.log.warning(
            f"Only {len(new_articles)} new articles found. Reusing {needed} previously processed ones to reach {config.maxArticles} total."
        )
        remaining = [a for a in all_articles_from_feed if a not in new_articles][:needed]
        new_articles.extend(remaining)

    Actor.log.info(f"Processing {len(new_articles)} total articles (including recycled ones if needed).")
    return {"articles": new_articles, "processed_count": 0}

async def process_and_save_article(state: WorkflowState) -> dict:
    articles = state["articles"]
    config = state["config"]
    processed_count = state["processed_count"]
    processed_urls_store = state["processed_urls_store"]

    if processed_count >= len(articles):
        Actor.log.info("No more articles to process.")
        return {"processed_count": processed_count}

    art = articles[processed_count]
    Actor.log.info(f"Processing article {processed_count + 1} of {len(articles)}: {art.link}")

    ai_overview = None
    
    # --- PRIORITY 1: Strict Quoted Title Search ("Title") ---
    query_strict = f"\"{art.title}\""
    Actor.log.info("Priority 1: Attempting strict DuckDuckGo search.")
    
    ai_overview = await fetch_summary_from_duckduckgo(
        query=query_strict, 
        is_test_mode=config.runTestMode,
        region=config.region, 
        time_limit=config.timeLimit
    )
    
    # --- PRIORITY 2: Less Restrictive Title Search (Title) ---
    if not ai_overview:
        query_loose = art.title.replace('"', '').strip() # Remove quotes if they were included
        Actor.log.warning("Priority 1 failed. Attempting Priority 2: Loose DuckDuckGo search.")
        
        ai_overview = await fetch_summary_from_duckduckgo(
            query=query_loose, 
            is_test_mode=config.runTestMode,
            region=config.region, 
            time_limit=config.timeLimit
        )

    # --- FALLBACK: Cleaned RSS Summary ---
    if not ai_overview and art.summary and len(art.summary.strip()) >= 50:
        Actor.log.warning("Priority 2 failed. Falling back to original RSS summary.")
        # Strip HTML before using the RSS summary
        ai_overview = strip_html_tags(art.summary)
        
    if not ai_overview:
        # UPDATED LOGIC: Skip article on failure instead of exiting actor
        Actor.log.error(f"❌ No AI summary could be generated for article {processed_count + 1}. Skipping to the next article.")
        return {"processed_count": processed_count + 1}

    art.summary = ai_overview
    analysis_results = await analyze_article_summary(art.summary, config.runTestMode)
    
    dataset_record = DatasetRecord(
        source=art.source,
        title=art.title,
        url=art.link,
        published=art.published,
        summary=art.summary,
        sentiment=analysis_results.get("sentiment"),
        category=analysis_results.get("category"),
        key_entities=analysis_results.get("key_entities")
    ).model_dump()

    await Actor.push_data([dataset_record])
    Actor.log.info(f"Pushed record for '{art.title[:50]}...' to dataset.")

    url_key = hashlib.md5(str(art.link).encode('utf-8')).hexdigest()
    await processed_urls_store.set_value(key=url_key, value=True)

    return {"processed_count": processed_count + 1}

def should_continue(state: WorkflowState) -> str:
    articles = state["articles"]
    processed_count = state["processed_count"]
    return "continue" if processed_count < len(articles) else "end"

async def main():
    async with Actor:
        input_data = await Actor.get_input()
        config = InputConfig(**input_data)
        Actor.log.info(f"Loaded config: {config}")

        # UPDATED: Only check for OPENAI_API_KEY
        if not config.runTestMode and not os.getenv("OPENAI_API_KEY"):
            Actor.log.error("❌ Missing required API key in environment variables (OPENAI_API_KEY). Aborting execution.")
            await Actor.exit(exit_code=1)
            return

        if config.runTestMode:
            Actor.log.warning("!!! ADMIN TEST MODE ACTIVE: Actor is bypassing ALL EXTERNAL API costs. !!!")

        processed_urls_store = await Actor.open_key_value_store(name="processed-urls-health")

        graph = StateGraph(WorkflowState)
        graph.add_node("RSSFetcher", rss_fetcher)
        graph.add_node("ProcessAndSaveArticle", process_and_save_article)
        graph.set_entry_point("RSSFetcher")

        graph.add_conditional_edges("RSSFetcher", should_continue, {"continue": "ProcessAndSaveArticle", "end": "__end__"})
        graph.add_conditional_edges("ProcessAndSaveArticle", should_continue, {"continue": "ProcessAndSaveArticle", "end": "__end__"})

        app = graph.compile()
        Actor.log.info("Starting Health & Fitness intelligence pipeline.")

        recursion_config = {"recursion_limit": config.maxArticles + 5}

        await app.ainvoke({
            "config": config,
            "articles": [],
            "processed_count": 0,
            "processed_urls_store": processed_urls_store
        }, config=recursion_config)

        Actor.log.info("🎯 Health & Fitness intelligence pipeline completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())