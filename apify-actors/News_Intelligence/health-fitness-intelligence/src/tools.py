import feedparser
import re
import os
# Removed httpx
import json
import asyncio
from typing import List, Dict, Any, Tuple
from apify import Actor
from apify_client import ApifyClient
from openai import OpenAI
from .models import RSSFeed
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

def init_openai() -> OpenAI:
    # The OpenAI client automatically looks for the OPENAI_API_KEY environment variable.
    return OpenAI()

# New categories for Health & Fitness
CATEGORIES = [
    "General Fitness/Training", "Nutrition/Recipes", "Wellness/Lifestyle",
    "Medical News/Research", "Fitness Business/Tech", "Product/Gear", "General Health"
]

def fetch_rss_feeds(source: str, custom_url: str = None, max_articles: int = 20) -> List[RSSFeed]:
    # New feed_map based on your provided URLs
    feed_map = {
        # General Fitness & Training
        "mens-health": "https://www.menshealth.com/rss/all.xml/",
        "myfitnesspal": "https://blog.myfitnesspal.com/feed",
        "born-fitness": "https://www.bornfitness.com/feed/",
        "trainerize": "http://feeds.feedburner.com/TrainerizeBlog",
        "wod-guru": "https://wod.guru/feed/",
        "breaking-muscle": "https://breakingmuscle.com/feed/",
        "fitnessista": "https://fitnessista.com/feed/",
        "anytime-fitness": "https://www.anytimefitness.co.in/feed/",
        "nasm": "https://blog.nasm.org/rss.xml",
        "girls-gone-strong": "https://www.girlsgonestrong.com/feed",
        "popsugar-fitness": "https://www.popsugar.com/feed",
        "the-fit-bits": "http://www.thefitbits.com/feed",

        # Nutrition & Healthy Eating
        "precision-nutrition": "https://www.precisionnutrition.com/feed",
        "bites-of-wellness": "https://bitesofwellness.com/feed/",
        "eating-bird-food": "https://www.eatingbirdfood.com/feed/",
        "nutrition-stripped": "https://nutritionstripped.com/articles/feed/",
        "oh-she-glows": "https://ohsheglows.com/feed/",
        "nutritionfacts": "https://nutritionfacts.org/feed/",
        "delish-knowledge": "https://www.delishknowledge.com/feed/",
        "real-food-dietitians": "https://therealfooddietitians.com/feed",
        "fit-foodie-finds": "https://fitfoodiefinds.com/feed/",
        "toby-amidor-nutrition": "https://tobyamidornutrition.com/feed",
        "pbfingers": "https://www.pbfingers.com/feed",
        "the-healthy-maven": "https://www.thehealthymaven.com/feed",
        "nutrition-twins": "https://www.nutritiontwins.com/feed",
        "the-full-helping": "https://www.thefullhelping.com/feed",
        "the-fit-foodie": "https://the-fit-foodie.com/feed",

        # Holistic Wellness & Lifestyle
        "fit-bottomed-girls": "https://fitbottomedgirls.com/category/fitness/fitness-blogs/feed/",
        "art-of-healthy-living": "https://artofhealthyliving.com/feed/",
        "shape": "https://feeds-api.dotdashmeredith.com/v1/rss/google/5814e1d4-bdb5-4afb-a458-61bfc1585860",
        "health": "https://feeds-api.dotdashmeredith.com/v1/rss/google/3a6c43d9-d394-4797-9855-97f429e5b1ff",
        "healthshots": "https://www.healthshots.com/rss-feeds/",
        "mommypotamus": "https://mommypotamus.com/feed",
        "natural-living-ideas": "https://www.naturallivingideas.com/feed",
        "a-healthy-slice-of-life": "https://www.ahealthysliceoflife.com/feed",
        "unlikely-martha": "https://unlikelymartha.com/feed",

        # Fitness Business & Tech
        "athletechnews": "https://athletechnews.com/feed",
        "health-club-management": "https://www.healthclubmanagement.co.uk/feed/news-feed.xml",
        "club-solutions": "https://clubsolutionsmagazine.com/feed/",
        "total-health-and-fitness": "https://www.totalhealthandfitness.com/feed/",
        "core-handf": "https://corehandf.com/blog/rss.xml",

        "custom": custom_url
    }
    
    urls = []
    if source == "custom" and custom_url: urls.append(custom_url)
    elif source == "all": urls = [url for key, url in feed_map.items() if key != "custom" and url is not None]
    else:
        if selected := feed_map.get(source): urls.append(selected)

    parsed_feeds = []
    for feed_url in urls:
        Actor.log.info(f"Parsing feed: {feed_url}")
        try:
            parsed = feedparser.parse(feed_url)
            if parsed.entries:
                source_title = parsed.feed.get("title", f"Unknown ({feed_url})")
                parsed_feeds.append((iter(parsed.entries), source_title))
            else: Actor.log.warning(f"Feed {feed_url} returned no entries.")
        except Exception as e: Actor.log.warning(f"Failed to parse feed {feed_url}: {e}")

    articles = []
    if len(parsed_feeds) > 1 and source == "all":
        available_feeds = list(parsed_feeds)
        while len(articles) < max_articles and available_feeds:
            feeds_to_remove = []
            for i, (entry_iterator, source_title) in enumerate(available_feeds):
                if len(articles) >= max_articles: break
                try:
                    entry = next(entry_iterator)
                    articles.append(RSSFeed(title=entry.get("title", ""), link=entry.get("link", ""), source=source_title, published=entry.get("published"), summary=entry.get("summary")))
                except StopIteration: feeds_to_remove.append(i)
                except Exception as e:
                    Actor.log.warning(f"Error reading entry from {source_title}, removing feed: {e}")
                    feeds_to_remove.append(i)
            for index in sorted(feeds_to_remove, reverse=True): available_feeds.pop(index)
    elif len(parsed_feeds) == 1:
        entry_iterator, source_title = parsed_feeds[0]
        for i, entry in enumerate(entry_iterator):
            if i >= max_articles: break
            articles.append(RSSFeed(title=entry.get("title", ""), link=entry.get("link", ""), source=source_title, published=entry.get("published"), summary=entry.get("summary")))
        Actor.log.info(f"Collected {len(articles)} articles from single source: {source_title}.")

    Actor.log.info(f"Collected a total of {len(articles)} articles.")
    return articles

async def summarize_snippets_with_llm(snippets: str, is_test_mode: bool) -> str:
    if is_test_mode: return "This is a test summary generated from dummy search snippets about a recent health or fitness trend."

    client = init_openai()
    prompt = f"Based on the following raw search result snippets, synthesize a concise, neutral, one-paragraph summary of the main news event.\n\nSnippets:\n---\n{snippets}\n---"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are a news summarization assistant. Generate a single coherent paragraph summarizing the provided search result snippets."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        summary = response.choices[0].message.content.strip()
        Actor.log.info("Successfully generated summary from search snippets.")
        return summary
    except Exception as e:
        Actor.log.warning(f"LLM summarization failed: {e}")
        return ""

async def fetch_summary_from_duckduckgo(query: str, is_test_mode: bool, region: str | None = None, time_limit: str | None = None) -> str:
    """
    Fetches snippets from DuckDuckGo and returns an LLM-generated summary.
    Replaces the old Google search function.
    """
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE ENABLED. Bypassing DuckDuckGo Search and LLM calls.")
        return await summarize_snippets_with_llm("", is_test_mode=True)

    # Prepare parameters for DDG
    time_param_for_api = None if time_limit and time_limit.lower() == 'any' else time_limit
    region_param_for_api = region 

    Actor.log.info(f"Searching DuckDuckGo News (Region: {region_param_for_api or 'any'}, Time: {time_param_for_api or 'any'}) for: {query[:60]}...")
    
    try:
        def run_langchain_search():
            wrapper = DuckDuckGoSearchAPIWrapper(
                region=region_param_for_api, 
                time=time_param_for_api, 
                max_results=5, 
                backend="news" # Focus search on news results
            )
            # Use DuckDuckGoSearchResults tool for structured output
            search_tool = DuckDuckGoSearchResults(
                api_wrapper=wrapper, 
                output_format="list",
                backend="news" 
            )
            return search_tool.invoke(query)

        search_results = await asyncio.to_thread(run_langchain_search)

    except Exception as e:
        Actor.log.error(f"An unexpected error occurred during DuckDuckGo (LangChain) search ({type(e).__name__}): {e}")
        return ""

    if not search_results:
        Actor.log.warning("DuckDuckGo (LangChain) search returned no items.")
        return ""

    # --- Build LLM prompt from snippets ---
    snippets_for_prompt = "\n".join(
        [f"Title: {item.get('title', 'N/A')}\nSnippet: {item.get('snippet', '')}" 
         for item in search_results if item.get('snippet')]
    )
    
    if not snippets_for_prompt:
        Actor.log.warning("No usable snippets found in search results.")
        return ""

    # Log the count of *usable* snippets
    usable_snippet_count = len([item for item in search_results if item.get('snippet')])
    Actor.log.info(f"Collected {usable_snippet_count} usable snippets from DuckDuckGo News.")

    return await summarize_snippets_with_llm(snippets_for_prompt, is_test_mode=False)


async def analyze_article_summary(summary: str, is_test_mode: bool) -> Dict[str, Any]:
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE: Bypassing LLM analysis call.")
        return {"sentiment": "General Info (TEST)", "category": "Nutrition/Recipes (TEST)", "key_entities": ["Vitamin D", "HIIT", "Wellness"]}

    client = init_openai()
    if not summary or len(summary) < 20:
        Actor.log.warning("Summary too short for analysis. Skipping LLM call.")
        return {"sentiment": "N/A", "category": "N/A", "key_entities": []}

    # Updated sentiment options for health context
    sentiment_options = ["High Importance (e.g., medical warning)", "Medium Importance (e.g., new study)", "General Info/Tip"]
    category_list_str = ", ".join(CATEGORIES)
    # Updated prompt
    prompt = f'Analyze the following Health & Fitness news summary: "{summary}"\n\nBased ONLY on the summary, provide a structured JSON output with:\n1. sentiment: The news importance level ({", ".join(sentiment_options)}).\n2. category: The best category from this list: {category_list_str}.\n3. key_entities: A list of up to 3 key ingredients, exercises, health concepts, or brands.\n\nOutput a single valid JSON object.'

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                # Updated system prompt
                {"role": "system", "content": "You are a professional Health & Fitness analyst. Return a JSON object with 'sentiment', 'category', and 'key_entities'."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        output_text = response.choices[0].message.content.strip()
        parsed = json.loads(output_text)
        entities = parsed.get("key_entities", [])
        if not isinstance(entities, list): entities = [str(entities)] if entities else []
        sentiment = str(parsed.get("sentiment", "N/A")).strip()
        if sentiment not in sentiment_options: sentiment = "General Info/Tip"
        return {"sentiment": sentiment, "category": str(parsed.get("category", "N/A")).strip(), "key_entities": entities}
    except Exception as e:
        Actor.log.warning(f"LLM analysis failed: {e}")
        return {"sentiment": "Error", "category": "Error", "key_entities": []}