from apify import Actor
from langgraph.graph import StateGraph
from typing import List, TypedDict, Any
import asyncio
from .models import RSSFeed, Article, InputConfig, DatasetRecord
from .tools import (
    fetch_rss_feeds,
    fetch_alpha_vantage_articles,
    analyze_article_summary,
    generate_llm_summary
)


# ---------------------------
# LangGraph Workflow State
# ---------------------------

class WorkflowState(TypedDict):
    """Defines the state passed between nodes in the LangGraph workflow."""
    config: InputConfig
    all_articles: List[Article] # Combined list for processing
    processed_count: int


# ---------------------------
# Node Functions
# ---------------------------

async def process_and_save_article(state: WorkflowState) -> dict:
    """
    Processes the next article. Runs LLM analysis for all articles, then LLM summarization.
    """
    all_articles = state["all_articles"]
    config = state["config"]
    processed_count = state["processed_count"]
    
    if processed_count >= len(all_articles):
        Actor.log.info("No more articles to process.")
        return {"processed_count": processed_count}


    art = all_articles[processed_count]
    
    # Initialize all fields with defaults
    article_sentiment = "N/A"
    article_category = "N/A"
    article_entities = []
    article_av_score = None
    
    Actor.log.info(f"Processing article {processed_count + 1} of {len(all_articles)} [Source: {art.source}]: {art.url}")
    
    # 1. Get Analysis Data (LLM analysis for all articles, using Gemini grounding)
    analysis_results = await analyze_article_summary(art, config.runTestMode)
    article_sentiment = analysis_results.get("sentiment")
    article_category = analysis_results.get("category")
    article_entities = analysis_results.get("key_entities")
    article_av_score = analysis_results.get("gdelt_tone")


    # 2. Perform LLM Summarization (Pay Point 2 - Optional for all articles)
    final_summary = art.summary
    
    if config.useSummarization:
        llm_summary = await generate_llm_summary(art, config.runTestMode)
        
        if llm_summary and not llm_summary.startswith("LLM Summary Error"):
            final_summary = llm_summary
        else:
            Actor.log.warning(f"LLM summarization failed. Keeping original summary or fallback.")
    else:
        Actor.log.info("LLM summarization skipped per user config.")

    # Update article object with final summary
    art.summary = final_summary
    
    # 3. Save the single article immediately to the dataset
    dataset_record = DatasetRecord(
        source=art.source,
        title=art.title,
        url=art.url,
        published=art.published,
        summary=art.summary if art.summary else "No summary available (LLM skipped or failed).",
        sentiment=article_sentiment,
        category=article_category,
        key_entities=article_entities,
        gdelt_tone=article_av_score
    ).model_dump() # <-- FIX: Changed .dict() to .model_dump() for Pydantic V2

    Actor.log.info(f"Pushing record for {art.title[:50]}... to dataset. Analysis: {article_sentiment}, {article_category}")
    await Actor.push_data([dataset_record])
    
    # 4. Update the processed count for the next iteration
    return {"processed_count": processed_count + 1}


def should_continue(state: WorkflowState) -> str:
    """Conditional edge to check if more articles need processing."""
    
    all_articles = state.get("all_articles", [])
    processed_count = state["processed_count"]
    
    if processed_count < len(all_articles):
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
        
        if config.runTestMode:
            Actor.log.warning("!!! ADMIN TEST MODE ACTIVE: Actor is bypassing ALL EXTERNAL API costs. !!!")

        
        # 1. Determine Fetch Strategy and Run Fetchers
        Actor.log.info("Starting Parallel Data Fetch (RSS and Alpha Vantage).")
        
        is_av_only_mode = (config.source == "Alpha Vantage News")
        
        rss_articles = []
        av_task = None
        
        if not is_av_only_mode:
            # Call synchronous RSS fetcher directly.
            rss_articles = fetch_rss_feeds(
                config.source, config.customFeedUrl, config.maxArticles
            )
        else:
            Actor.log.info("Running in dedicated Alpha Vantage News mode. Skipping RSS feeds.")
        
        # Call AV fetcher as an asynchronous task
        av_task = asyncio.create_task(fetch_alpha_vantage_articles(
            config.source, config.maxArticles, config.runTestMode
        ))
        
        # Wait for the AV task to complete
        av_articles = await av_task
        
        # Combine articles into one list
        all_articles = rss_articles + av_articles
        
        Actor.log.info(f"Combined {len(rss_articles)} RSS articles and {len(av_articles)} AV articles for a total of {len(all_articles)} articles to process.")
        
        if not all_articles:
            Actor.log.warning("No articles collected from any source. Finishing pipeline.")
            return
            
        # 2. Setup LangGraph for Iterative Processing Loop
        graph = StateGraph(WorkflowState)
        graph.add_node("ProcessAndSaveArticle", process_and_save_article)
        graph.set_entry_point("ProcessAndSaveArticle")
        
        graph.add_conditional_edges(
            "ProcessAndSaveArticle",
            should_continue,
            {"continue": "ProcessAndSaveArticle", "end": "__end__"}
        )

        app = graph.compile()
        
        Actor.log.info("Starting iterative processing loop (Gemini Analysis/Summarization).")
        
        # Initial state for the loop contains the combined articles
        initial_state = {
            "config": config,
            "all_articles": all_articles,
            "processed_count": 0
        }
        
        # <-- FIX: Set recursion limit dynamically based on max articles from both sources
        # Add a small buffer to be safe.
        max_total_articles = config.maxArticles * 2 + 5
        recursion_config = {"recursion_limit": max_total_articles}

        await app.ainvoke(initial_state, config=recursion_config)

        Actor.log.info("🎯 Global Markets Intelligence pipeline completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())