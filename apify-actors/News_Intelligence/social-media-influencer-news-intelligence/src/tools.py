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
# New imports for DuckDuckGo
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

def init_openai() -> OpenAI:
    # The OpenAI client automatically looks for the OPENAI_API_KEY environment variable.
    return OpenAI()

# New categories for Social Media & Influencer Marketing
CATEGORIES = [
    "Platform News", "Strategy/Trends", "Influencer Marketing",
    "Analytics/Tools", "Case Study/Campaign", "Regulation/Policy", "General Marketing"
]

def fetch_rss_feeds(source: str, custom_url: str = None, max_articles: int = 20) -> List[RSSFeed]:
    # New feed_map based on your provided URLs
    feed_map = {
        "later": "https://later.com/rss.xml",
        "digital-agency-network": "https://digitalagencynetwork.com/feed",
        "kofluence": "https://www.kofluence.com/feed",
        "influencity": "https://influencity.com/blog/en/rss.xml",
        "traackr": "http://www.traackr.com/blog/rss.xml",
        "crazyegg": "https://www.crazyegg.com/blog/feed/",
        "upfluence": "https://www.upfluence.com/feed",
        "influencer-marketing-hub": "https://influencermarketinghub.com/feed",
        "iamwiim": "https://iamwiim.com/feed",
        "the-shelf": "https://www.theshelf.com/feed",
        "sproutsocial": "https://sproutsocial.com/insights/feed/",
        "grin": "https://grin.co/feed/",
        "modash": "https://www.modash.io/blog/rss.xml",
        "creatoriq": "https://www.creatoriq.com/blog/rss.xml",
        "influencer-nexus": "https://influencernexus.com/feed/",
        "hootsuite": "https://blog.hootsuite.com/feed",
        "emplifi": "https://emplifi.io/resource-type/blogs/feed/",
        "buffer": "https://buffer.com/resources/rss/",
        "webfluential": "https://blog.webfluential.com/feed",
        "social-media-examiner": "https://www.socialmediaexaminer.com/feed",
        "neal-schaffer": "https://nealschaffer.com/feed/",
        "strike-social": "https://strikesocial.com/feed/",
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
    if is_test_mode: return "This is a test summary generated from dummy search snippets about a recent social media marketing event."

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

async def fetch_summary_from_duckduckgo(
    query: str, 
    is_test_mode: bool, 
    region: str | None = None, 
    time_limit: str | None = None 
) -> str:
    """
    Fetches snippets from DuckDuckGo and returns an LLM-generated summary.
    """
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE ENABLED. Bypassing DuckDuckGo Search and LLM calls.")
        return await summarize_snippets_with_llm("", is_test_mode=True)

    # Prepare parameters
    # The DDG API wrapper expects 'None' or an empty string for no time limit, not 'any'
    time_param_for_api = None if time_limit and time_limit.lower() == 'any' else time_limit
    region_param_for_api = region 

    Actor.log.info(f"Searching DuckDuckGo News (Region: {region_param_for_api or 'any'}, Time: {time_param_for_api or 'any'}) for: {query[:60]}...")
    
    try:
        def run_langchain_search():
            wrapper = DuckDuckGoSearchAPIWrapper(
                region=region_param_for_api, 
                time=time_param_for_api, 
                max_results=5, # Fetch top 5 snippets
                source="news" # Focus search on news results
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
    snippets_for_prompt = "\n---\n".join(
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
        return {"sentiment": "Medium Impact (TEST)", "category": "Strategy/Trends (TEST)", "key_entities": ["TikTok", "Instagram", "New Feature"]}

    client = init_openai()
    if not summary or len(summary) < 20:
        Actor.log.warning("Summary too short for analysis. Skipping LLM call.")
        return {"sentiment": "N/A", "category": "N/A", "key_entities": []}

    # Updated sentiment options for marketing context
    sentiment_options = ["High Impact", "Medium Impact", "Low Impact/Informational"]
    category_list_str = ", ".join(CATEGORIES)
    # Updated prompt
    prompt = f'Analyze the following Social Media & Marketing news summary: "{summary}"\n\nBased ONLY on the summary, provide a structured JSON output with:\n1. sentiment: The news impact level ({", ".join(sentiment_options)}).\n2. category: The best category from this list: {category_list_str}.\n3. key_entities: A list of up to 3 key companies, platforms, or marketing concepts.\n\nOutput a single valid JSON object.'

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                # Updated system prompt
                {"role": "system", "content": "You are a professional Social Media & Marketing analyst. Return a JSON object with 'sentiment', 'category', and 'key_entities'."},
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
        if sentiment not in sentiment_options: sentiment = "Low Impact/Informational"
        return {"sentiment": sentiment, "category": str(parsed.get("category", "N/A")).strip(), "key_entities": entities}
    except Exception as e:
        Actor.log.warning(f"LLM analysis failed: {e}")
        return {"sentiment": "Error", "category": "Error", "key_entities": []}