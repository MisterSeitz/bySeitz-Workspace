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
    return OpenAI()

CATEGORIES = [
    "Vulnerability/CVE", "Malware/Ransomware", "Policy/Compliance",
    "Data Breach/Hack", "Threat Intelligence", "Cloud Security",
    "IoT/Hardware", "General InfoSec"
]

def fetch_rss_feeds(source: str, custom_url: str = None, max_articles: int = 10) -> List[RSSFeed]:
    # ... (rest of the function remains the same) ...
    feed_map = {
        "the-hacker-news": "https://feeds.feedburner.com/TheHackersNews",
        "krebsonsecurity": "https://krebsonsecurity.com/feed/",
        "dark-reading": "https://www.darkreading.com/rss.xml",
        "schneier": "https://www.schneier.com/feed/atom",
        "cisa-advisories": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
        "bleepingcomputer": "https://www.bleepingcomputer.com/feed/",
        "cso-online": "https://www.csoonline.com/feed/",
        "rapid7": "https://blog.rapid7.com/rss/",
        "microsoft-security": "https://www.microsoft.com/security/blog/feed",
        "google-security": "https://googleonlinesecurity.blogspot.com/atom.xml",
        "zdnet-security": "https://www.zdnet.com/topic/security/rss.xml",
        "arstechnica-security": "https://arstechnica.com/tag/security/feed",
        "threatpost": "https://threatpost.com/feed",
        "security-affairs": "http://securityaffairs.co/wordpress/feed",
        "naked-security": "https://nakedsecurity.sophos.com/feed",
        "troy-hunt": "https://feeds.feedburner.com/TroyHunt",
        "zdi-published": "https://www.zerodayinitiative.com/rss/published/",
        "cisco-talos": "https://feeds.feedburner.com/feedburner/Talos",
        "crowdstrike": "https://www.crowdstrike.com/blog/feed",
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
    # ... (rest of the function remains the same) ...
    if is_test_mode: return "This is a test summary generated from dummy search snippets. It notes that Source A reported a vulnerability while Source B downplayed the risk, showcasing a variation in reporting."

    client = init_openai()
    prompt = f"Synthesize a concise, neutral, one-paragraph summary of the main news event from the following search results. Note the different sources and dates, and **briefly mention any significant variations in their reporting (e.g., conflicting facts, different sentiment)**.\n\nSnippets:\n---\n{snippets}\n---"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are a news summarization assistant. Your goal is to synthesize a single, coherent paragraph from multiple sourced snippets. Base your summary *only* on the snippets. If you detect notable differences in reporting between sources, briefly mention it."},
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
        sources = [{"title": "Test Source A", "url": "https://example.com/a", "source": "TestNews", "date": "2025-10-19"}]
        return summary, sources

    # --- Prepare parameters, passing defaults directly if needed ---
    # Handle 'any' time limit specifically if the API expects None for no limit,
    # otherwise pass the string 'any' or the specific limit ('d', 'w', 'm')
    time_param_for_api = None if time_limit and time_limit.lower() == 'any' else time_limit
    # Pass the region string directly, including 'wt-wt' if that's the input
    region_param_for_api = region 

    Actor.log.info(f"Searching DuckDuckGo News (Region: {region_param_for_api or 'any'}, Time: {time_param_for_api or 'any'}) for: {query[:60]}...")
    
    try:
        def run_langchain_search():
            # --- Pass parameters directly to the wrapper ---
            wrapper = DuckDuckGoSearchAPIWrapper(
                region=region_param_for_api, 
                time=time_param_for_api, 
                max_results=20 # <-- Increased from 10 to 20 to get more snippets
            )
            search_tool = DuckDuckGoSearchResults(
                api_wrapper=wrapper, 
                output_format="list",
                backend="news" 
            )
            return search_tool.invoke(query)

        search_results = await asyncio.to_thread(run_langchain_search)

    except Exception as e:
        # Log the specific exception type and message for better debugging
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
    # ... (rest of the function remains the same) ...
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE: Bypassing LLM analysis call.")
        return {"sentiment": "Negative (TEST)", "category": "Vulnerability/CVE (TEST)", "key_entities": ["CISA", "Microsoft", "APT4B"]}

    client = init_openai()
    if not summary or len(summary) < 20:
        Actor.log.warning("Summary too short for analysis. Skipping LLM call.")
        return {"sentiment": "N/A", "category": "N/A", "key_entities": []}

    sentiment_options = ["High Risk", "Medium Risk", "Low Risk/Informational"]
    category_list_str = ", ".join(CATEGORIES)
    prompt = f'Analyze the following Cybersecurity news summary: "{summary}"\n\nBased ONLY on the summary, provide a structured JSON output with:\n1. sentiment: The risk/impact level ({", ".join(sentiment_options)}).\n2. category: The best category from this list: {category_list_str}.\n3. key_entities: A list of up to 3 key companies, groups, or vulnerabilities.\n\nOutput a single valid JSON object.'

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are a professional Cybersecurity analyst. Return a JSON object with 'sentiment', 'category', and 'key_entities'."},
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
        if sentiment not in sentiment_options: sentiment = "Low Risk/Informational"
        return {"sentiment": sentiment, "category": str(parsed.get("category", "N/A")).strip(), "key_entities": entities}
    except Exception as e:
        Actor.log.warning(f"LLM analysis failed: {e}")
        return {"sentiment": "Error", "category": "Error", "key_entities": []}