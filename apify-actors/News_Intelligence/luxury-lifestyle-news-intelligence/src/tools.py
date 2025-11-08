import feedparser
import re
import os
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
    # This function relies on the OPENAI_API_KEY environment variable being set.
    return OpenAI()

# --- AMENDED CATEGORIES FOR LUXURY & LIFESTYLE ---
CATEGORIES = [
    "Luxury Retail/Apparel", "Automotive/Yachts/Aviation", "Travel/Hospitality/Experiences",
    "High-End Real Estate/Design", "Watches/Jewelry", "Art/Collectibles/Auctions",
    "Wealth Management/High Net Worth (HNW) Trends", "Digital Luxury/Web3/Metaverse"
]

def fetch_rss_feeds(source: str, custom_url: str = None, max_articles: int = 10) -> List[RSSFeed]:
    # --- AMENDED FEED MAP FOR LUXURY & LIFESTYLE ---
    luxury_daily_feeds = [
        "https://www.luxurydaily.com/category/resources/news-briefs/feed/",
        "https://www.luxurydaily.com/category/news/research/feed/",
        "https://www.luxurydaily.com/category/news/events/feed/",
        "https://www.luxurydaily.com/category/news/commerce-news/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/food-and-beverage/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/fragrance-and-personal-care/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/apparel-and-accessories/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/financial-services/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/education/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/consumer-packaged-goods/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/consumer-electronics/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/automotive-industry-sectors/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/arts-and-entertainment/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/government/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/healthcare/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/home-furnishings/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/jewelry/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/legal-and-privacy/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/marketing-industry-sectors/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/mediapublishing/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/nonprofits/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/real-estate/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/retail-industry-sectors/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/software-and-technology-industry-sectors/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/sports/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/telecommunications/feed/rss/",
        "https://www.luxurydaily.com/category/sectors/travel-and-hospitality/feed/rss/",
        "https://www.luxurydaily.com/category/opinion/blog/feed/rss/",
        "https://www.luxurydaily.com/category/opinion/classic-guides/feed/rss/",
        "https://www.luxurydaily.com/category/opinion/columns/feed/rss/",
        "https://www.luxurydaily.com/category/opinion/editorials/feed/rss/",
        "https://www.luxurydaily.com/category/opinion/letters/feed/rss/",
    ]
    
    feed_map = {
        "trulyclassy": "https://www.trulyclassy.com/feed/",
        "luxurylaunches": "https://luxurylaunches.com/web-stories/feed/",
        "robbreport_lifestyle": "https://robbreport.com/lifestyle/feed/",
        "robbreport_main": "https://robbreport.com/feed/",
        "theluxuryeditor": "https://theluxuryeditor.com/feed/",
        "luxurynewsonline": "https://luxurynewsonline.com/feed/",
        "afluxurylifestyle": "https://afluxurylifestyle.com/feed",
        "luxuo": "https://www.luxuo.com/feed",
        "luxebible": "https://luxebible.com/category/lifestyle/feed/",
        "luxurialifestyle": "https://www.luxurialifestyle.com/feed/", # Duplicate feed removed: https://www.luxurialifestyle.com/feed/
        "luxuryendless": "https://www.luxuryendless.com/lifestyle?format=rss",
        "lux_life": "https://lux-life.digital/feed/",
        "serrarigroup": "https://serrarigroup.com/feed/",
        "tempusmagazine": "https://tempusmagazine.co.uk/feed",
        "wmwnewsglobal": "https://www.wmwnewsglobal.com/feed/",
        "luxurydaily": luxury_daily_feeds, # Concatenated feed
        "custom": custom_url
    }
    # -----------------------------------------------
    
    urls = []
    if source == "custom" and custom_url: urls.append(custom_url)
    elif source == "all": 
        for key, value in feed_map.items():
            if key != "custom" and value is not None:
                if isinstance(value, list):
                    urls.extend(value)
                else:
                    urls.append(value)
    else:
        selected = feed_map.get(source)
        if selected:
            if isinstance(selected, list):
                urls.extend(selected)
            else:
                urls.append(selected)

    parsed_feeds = []
    for feed_url in urls:
        Actor.log.info(f"Parsing feed: {feed_url}")
        try:
            parsed = feedparser.parse(feed_url)
            if parsed.entries:
                source_title = parsed.feed.get("title", f"Unknown ({feed_url})")
                # Special handling to consolidate source title for Luxury Daily feeds
                if "luxurydaily.com" in feed_url:
                    source_title = "Luxury Daily"
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
    if is_test_mode: return "This is a test summary generated from dummy search snippets. It notes that Source A reported a surge in single-family home prices in Miami while Source B focused on the resulting lack of affordability for first-time buyers, showcasing a variation in reporting."

    client = init_openai()
    # --- AMENDED PROMPT FOR LUXURY & LIFESTYLE ---
    prompt = f"Synthesize a concise, neutral, one-paragraph summary of the main Luxury, High-End Market, or Lifestyle news event from the following search results. Note the different sources and dates, and **briefly mention any significant variations in their reporting (e.g., conflicting facts, different focus, or opposing perspectives)**.\n\nSnippets:\n---\n{snippets}\n---"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are a Luxury and Lifestyle news summarization assistant. Your goal is to synthesize a single, coherent paragraph from multiple sourced snippets. Base your summary *only* on the snippets. If you detect notable differences in reporting between sources, briefly mention it."},
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


async def fetch_summary_from_duckduckgo(
    query: str, 
    is_test_mode: bool, 
    region: str | None = None, 
    time_limit: str | None = None 
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Fetches snippets from DuckDuckGo and returns a summary and the list of sources.
    """
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE ENABLED. Bypassing DuckDuckGo Search and LLM calls.")
        summary = await summarize_snippets_with_llm("", is_test_mode=True)
        sources = [{"title": "Test Source A", "url": "https://example.com/a", "source": "TestRobbReport", "date": "2025-10-19"}]
        return summary, sources

    # --- Prepare parameters, passing defaults directly if needed ---
    time_param_for_api = None if time_limit and time_limit.lower() == 'any' else time_limit
    region_param_for_api = region 

    Actor.log.info(f"Searching DuckDuckGo News (Region: {region_param_for_api or 'any'}, Time: {time_param_for_api or 'any'}) for: {query[:60]}...")
    
    try:
        def run_langchain_search():
            wrapper = DuckDuckGoSearchAPIWrapper(
                region=region_param_for_api, 
                time=time_param_for_api, 
                max_results=20 
            )
            search_tool = DuckDuckGoSearchResults(
                api_wrapper=wrapper, 
                output_format="list",
                backend="news" 
            )
            return search_tool.invoke(query)

        search_results = await asyncio.to_thread(run_langchain_search)

    except Exception as e:
        Actor.log.error(f"An unexpected error occurred during DuckDuckGo (LangChain) search ({type(e).__name__}): {e}")
        return "", []

    if not search_results:
        Actor.log.warning("DuckDuckGo (LangChain) search returned no items.")
        return "", []

    # --- Build prompt and sources list (no changes) ---
    snippets_for_prompt = "\n---\n".join(
        [f"Source: {item.get('source', 'Unknown')}\nDate: {item.get('date', 'N/A')}\nTitle: {item.get('title', 'N/A')}\nSnippet: {item.get('snippet', '')}" 
         for item in search_results if item.get('snippet')]
    )
    
    snippet_sources_list = [
        {
            "title": item.get('title', 'Unknown'), 
            "url": item.get('link', 'N/A'),
            "source": item.get('source', 'Unknown'),
            "date": item.get('date', 'N/A')
        } 
        for item in search_results if item.get('snippet')
    ]

    Actor.log.info(f"Collected {len(snippet_sources_list)} snippets from DuckDuckGo News.")
    
    summary = await summarize_snippets_with_llm(snippets_for_prompt, is_test_mode=False)
    
    return summary, snippet_sources_list


async def analyze_article_summary(summary: str, is_test_mode: bool) -> Dict[str, Any]:
    if is_test_mode:
        # --- AMENDED TEST RESPONSE FOR LUXURY & LIFESTYLE ---
        Actor.log.warning("ADMIN TEST MODE: Bypassing LLM analysis call.")
        return {"sentiment": "Brand Growth (TEST)", "category": "Automotive/Yachts/Aviation (TEST)", "key_entities": ["Ferrari", "Monaco Yacht Show", "LVMH"]}
        # -----------------------------------------------

    client = init_openai()
    if not summary or len(summary) < 20:
        Actor.log.warning("Summary too short for analysis. Skipping LLM call.")
        return {"sentiment": "N/A", "category": "N/A", "key_entities": []}

    # --- AMENDED SENTIMENT OPTIONS FOR LUXURY & LIFESTYLE ---
    sentiment_options = ["Brand Growth", "Market Downturn", "Acquisition/Partnership", "Informational"]
    category_list_str = ", ".join(CATEGORIES)
    prompt = f'Analyze the following Luxury and Lifestyle news summary: "{summary}"\n\nBased ONLY on the summary, provide a structured JSON output with:\n1. sentiment: The market dynamic or impact level ({", ".join(sentiment_options)}).\n2. category: The best category from this list: {category_list_str}.\n3. key_entities: A list of up to 3 key brands, events, companies, or people mentioned.\n\nOutput a single valid JSON object.'

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are a professional Luxury and Lifestyle market analyst. Return a JSON object with 'sentiment', 'category', and 'key_entities'."},
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
        if sentiment not in sentiment_options: sentiment = "Informational"
        return {"sentiment": sentiment, "category": str(parsed.get("category", "N/A")).strip(), "key_entities": entities}
    except Exception as e:
        Actor.log.warning(f"LLM analysis failed: {e}")
        return {"sentiment": "Error", "category": "Error", "key_entities": []}