from apify import Actor
from langgraph.graph import StateGraph
from typing import List, TypedDict
import asyncio
from .models import RSSFeed, Article, InputConfig, DatasetRecord
from .tools import fetch_rss_feeds, fetch_summary_from_google, analyze_article_summary


# ---------------------------
# LangGraph Workflow State
# ---------------------------

class WorkflowState(TypedDict):
    """Defines the state passed between nodes in the LangGraph workflow."""
    config: InputConfig
    articles: List[Article]
    processed_count: int


# ---------------------------
# Node Functions
# ---------------------------

# EXCLUDED_URL_SEGMENTS are now obsolete
EXCLUDED_URL_SEGMENTS = [
    "/podcasts/", 
    "/video/", 
    "/live/",
    "/multimedia/", 
    "/interactive/",
    "/market-data/",
    "/columns/",
    "/tools/",
    "/charts/" 
]

async def rss_fetcher(state: WorkflowState) -> dict:
    """Fetch RSS feeds and convert entries to Article objects."""

    config = state["config"]

    rss_entries = fetch_rss_feeds(
        config.source,
        custom_url=config.customFeedUrl,
        max_articles=config.maxArticles
    )

    articles = []
    for entry in rss_entries:
        article = Article(
            title=entry.title,
            url=entry.link,
            source=entry.source,
            published=entry.published,
            summary=entry.summary,
        )
        articles.append(article)
        
    Actor.log.info(f"Successfully collected {len(articles)} articles from RSS feeds.")

    return {"articles": articles, "processed_count": 0}


async def process_and_save_article(state: WorkflowState) -> dict:
    """Processes the next article, gets summary via Google Search/Test Mode, analyzes it, and saves it."""

    articles = state["articles"]
    config = state["config"]
    processed_count = state["processed_count"]
    
    if processed_count >= len(articles):
        Actor.log.info("No more articles to process.")
        return {"processed_count": processed_count}


    art = articles[processed_count]
    article_sentiment = "N/A"
    article_category = "N/A"
    article_entities = []

    Actor.log.info(f"Processing article {processed_count + 1} of {len(articles)}: {art.url}")
    
    # 1. Get AI Overview via Google Search (Pay Point 1) OR Test Mode
    query = f"{art.title} {art.source}" 
    
    # Pass the runTestMode flag to the Google Search fetcher
    ai_overview = await fetch_summary_from_google(query, config.runTestMode)
    
    if ai_overview:
        art.summary = ai_overview
        
        # Report cost for Google Search run (Pay Point 1) ONLY IF NOT IN TEST MODE
        if not config.runTestMode:
            try:
                # Pushes the 'article-fetch' event for the Google Search run
                await Actor.push_actor_event( 
                    event_name='article-fetch',
                    event_data={'value': 1} 
                )
            except Exception as e:
                Actor.log.warning(f"Google Search cost reporting failed. Skipping event push: {e}")
        
        # 2. Perform Combined LLM Analysis (Pay Point 2)
        # 💡 FIX 2: Pass the runTestMode flag to the analysis function
        analysis_results = await analyze_article_summary(art.summary, config.runTestMode)
        
        # Extract and store analysis results
        article_sentiment = analysis_results.get("sentiment")
        article_category = analysis_results.get("category")
        article_entities = analysis_results.get("key_entities")
        
    else:
        Actor.log.warning(f"Failed to get AI Overview. Skipping LLM analysis.")

    
    # 3. Save the single article immediately to the dataset
    dataset_record = DatasetRecord(
        source=art.source,
        title=art.title,
        url=art.url,
        published=art.published,
        summary=art.summary if art.summary else "No summary available (Google search failed).",
        sentiment=article_sentiment,
        category=article_category,
        key_entities=article_entities
    ).dict()

    Actor.log.info(f"Pushing record for {art.title[:50]}... to dataset.")
    await Actor.push_data([dataset_record]) 
    
    # 4. Update the processed count for the next iteration
    return {"processed_count": processed_count + 1}


def should_continue(state: WorkflowState) -> str:
    """Conditional edge to check if more articles need processing."""
    
    articles = state["articles"]
    processed_count = state["processed_count"]
    
    if processed_count < len(articles):
        return "continue"
    else:
        return "end"


# ---------------------------
# Main Entry Point
# ---------------------------

async def main():
    """Main entrypoint for Apify actor execution."""
    async with Actor:
        input_data = await Actor.get_input()
        
        config = InputConfig(**input_data)
        Actor.log.info(f"Loaded config: {config}")
        
        # Log test mode status
        if config.runTestMode:
            Actor.log.warning("!!! ADMIN TEST MODE ACTIVE: Actor is bypassing ALL EXTERNAL API costs. !!!")


        # LangGraph setup for iterative processing
        graph = StateGraph(WorkflowState)

        graph.add_node("RSSFetcher", rss_fetcher)
        graph.add_node("ProcessAndSaveArticle", process_and_save_article)
        
        graph.set_entry_point("RSSFetcher")
        
        graph.add_conditional_edges(
            "RSSFetcher",
            should_continue, 
            {"continue": "ProcessAndSaveArticle", "end": "__end__"}
        )
        
        graph.add_conditional_edges(
            "ProcessAndSaveArticle",
            should_continue,
            {"continue": "ProcessAndSaveArticle", "end": "__end__"}
        )

        app = graph.compile()

        Actor.log.info("Starting Venture Capital intelligence pipeline (2 Pay Points: Google Search AI Mode + LLM Analysis).")
        await app.ainvoke({
            "config": config,
            "articles": [],
            "processed_count": 0
        })

        Actor.log.info("🎯 Venture Capital intelligence pipeline completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())