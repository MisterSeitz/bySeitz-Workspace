import feedparser
import re
from typing import List, Tuple, Dict, Any
from apify import Actor
from apify_client import ApifyClient
from openai import OpenAI
from .models import RSSFeed, Article, SummaryResult
import json


# Initialize Apify Client
def init_apify_client() -> ApifyClient:
    """Initializes the Apify client."""
    return ApifyClient()

# Initialize OpenAI
def init_openai() -> OpenAI:
    """Initializes the OpenAI client."""
    return OpenAI()

# Global categories for the model to choose from (VC focused)
CATEGORIES = [
    "Funding Round", "Acquisition/Exit", "IPO/Public Listing", "Policy/Regulation", 
    "Venture Strategy", "Founders/Talent", "Market Analysis", "Product Launch", 
    "Layoffs", "General Tech"
]

# -------------------------------
# 1️⃣ Fetch RSS Feeds by Source (No Change)
# -------------------------------
def fetch_rss_feeds(source: str, custom_url: str = None, max_articles: int = 20) -> List[RSSFeed]:
    """Fetch and parse RSS feed entries for the selected VC sources."""

    # 🔹 Venture Capital Feed Map (VC Niche)
    feed_map = {
        "techcrunch": "https://feeds.feedburner.com/TechCrunch/startups",
        "crunchbase": "https://news.crunchbase.com/feed/",
        "forbes-vc": "https://www.forbes.com/venture-capital/feed/",
        "custom": None
    }

    urls = []
    if source == "custom" and custom_url:
        urls = [custom_url]
    else:
        selected = feed_map.get(source)
        if selected:
            urls = [selected]
        elif source == "all":
            urls = list(feed_map.values())
            
    # List to hold (feed_iterator, source_title) for collection
    parsed_feeds = [] 
    
    # First pass: Parse all selected feeds
    for feed_url in urls:
        Actor.log.info(f"Parsing feed: {feed_url}")
        try:
            parsed = feedparser.parse(feed_url)
            
            # Check if the feed has entries and a title
            if parsed.entries:
                source_title = parsed.feed.get("title", f"Unknown ({feed_url})")
                
                # Store entries as an iterator for efficient round-robin
                parsed_feeds.append((iter(parsed.entries), source_title))
            else:
                Actor.log.warning(f"Feed {feed_url} returned no entries.")

        except Exception as e:
            Actor.log.warning(f"Failed to parse feed {feed_url}: {e}")
            
    articles = []
    
    # Collection logic remains the same (round-robin for 'all')
    if len(parsed_feeds) > 1 and source == "all":
        
        available_feeds = list(parsed_feeds)

        # Round-robin collection for 'all' sources
        while len(articles) < max_articles and available_feeds:
            feeds_to_remove = []

            for i, (entry_iterator, source_title) in enumerate(available_feeds):
                if len(articles) >= max_articles:
                    break
                    
                try:
                    entry = next(entry_iterator)
                    
                    rss_item = RSSFeed(
                        title=entry.get("title", ""),
                        link=entry.get("link", ""),
                        source=source_title,
                        published=entry.get("published", None),
                        summary=entry.get("summary", None),
                    )
                    articles.append(rss_item)
                    
                except StopIteration:
                    feeds_to_remove.append(i)
                except Exception as e:
                    Actor.log.warning(f"Error reading entry from {source_title}, removing feed: {e}")
                    feeds_to_remove.append(i)

            for index in sorted(feeds_to_remove, reverse=True):
                available_feeds.pop(index)
    
    elif len(parsed_feeds) >= 1:
        entry_iterator, source_title = parsed_feeds[0]
        
        for i, entry in enumerate(entry_iterator):
            if i >= max_articles:
                break
            
            rss_item = RSSFeed(
                title=entry.get("title", ""),
                link=entry.get("link", ""),
                source=source_title,
                published=entry.get("published", None),
                summary=entry.get("summary", None),
            )
            articles.append(rss_item)
            
        Actor.log.info(f"Collected {len(articles)} articles from single source: {source_title}.")


    Actor.log.info(f"Collected a total of {len(articles)} articles.")
    return articles


# -------------------------------
# 2️⃣ Fetch Summary via Google Search AI Overview (Pay Point 1)
# -------------------------------
async def fetch_summary_from_google(query: str, is_test_mode: bool) -> str:
    """
    Runs the Google Search Results Scraper OR returns dummy data if test mode is enabled.
    """
    
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE ENABLED. Bypassing Google Search Actor call and Pay Point 1.")
        # VC-specific dummy summary for testing consistency
        return f"TEST MODE SUMMARY: Startup {query.split()[0]} secured a $50M Series B round led by Sequoia Capital, valuing the company at $500M. The funding will be used to expand into the AI infrastructure market, signaling strong positive sentiment for early-stage enterprise SaaS."
        

    client = init_apify_client()
    
    GOOGLE_SEARCH_ACTOR_ID = "apify/google-search-results" 

    Actor.log.info(f"Searching Google for summary (AI Mode): {query[:50]}...")
    
    search_input = {
        "queries": [query],
        "aiMode": "aiModeOnly", 
        "maxPagesPerQuery": 1,
        "resultsPerPage": 100, 
        "maxResults": 1, 
        "mobileResults": False,
        "forceExactMatch": False,
        "includeIcons": False,
        "includeUnfilteredResults": False,
        "focusOnPaidAds": False,
        "maximumLeadsEnrichmentRecords": 0,
        "saveHtml": False,
        "saveHtmlToKeyValueStore": False 
    }

    try:
        run = await client.actor(GOOGLE_SEARCH_ACTOR_ID).call(
            run_input=search_input
        )
        
        dataset = client.dataset(run["defaultDatasetId"])
        items = await dataset.list_items()
        
        if items and items["items"]:
            ai_overview_text = items["items"][0].get("aiOverview")
            
            if ai_overview_text:
                Actor.log.info("Successfully retrieved AI Overview from Google Search (Pay Point 1).")
                return ai_overview_text.strip()
        
        Actor.log.warning(f"Google Search AI Overview not found for query: {query}")
        return ""

    except Exception as e:
        Actor.log.error(f"Google Search Actor failed: {e}. Check token/plan status.")
        return ""


# -------------------------------
# 3️⃣ Combined LLM Analysis (Pay Point 2)
# -------------------------------
async def analyze_article_summary(summary: str, is_test_mode: bool) -> Dict[str, Any]:
    """
    Performs combined LLM analysis OR returns static dummy data if test mode is enabled.
    """
    
    # 💡 FIX 1: Bypass LLM cost if in test mode
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE: Bypassing LLM analysis (Pay Point 2 cost skipped).")
        # Return structured dummy data for validation
        return {
            "sentiment": "Positive (TEST)",
            "category": "Funding Round (TEST)",
            "key_entities": ["Startup X", "Investor Y"]
        }

    client = init_openai()
    
    if not summary or len(summary) < 50:
        Actor.log.warning("Summary too short for analysis. Skipping LLM call (Pay Point 2 skipped).")
        return {"sentiment": "N/A", "category": "N/A", "key_entities": []}

    sentiment_options = ["Positive", "Neutral", "Negative"]
    category_list_str = ", ".join(CATEGORIES)
    
    prompt = f"""
    Analyze the following Venture Capital news summary: "{summary}"

    Based ONLY on the summary, provide a structured JSON output with the following analysis:
    1.  **sentiment**: The overall mood regarding the funding/event. Must be one of: {', '.join(sentiment_options)}.
    2.  **category**: The single best category from this list: {category_list_str}.
    3.  **key_entities**: A list of up to 3 major companies (startup/acquirer), investors (VC firms), or founders explicitly named. If none are found, use an empty list: [].

    Your entire output MUST be a single, valid JSON object matching the requested schema.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125", 
            messages=[
                {"role": "system", "content": "You are a professional Venture Capital analyst. You MUST return a single valid JSON object with keys: 'sentiment' (string), 'category' (string), and 'key_entities' (list of strings). DO NOT include any other text or markdown outside of the JSON object."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}, 
        )
        output_text = response.choices[0].message.content.strip()

        # Report tokens for Pay Point 2 (LLM Cost)
        tokens = response.usage.total_tokens
        if tokens > 0:
            Actor.log.info(f"Reporting {tokens} tokens used for combined analysis (Pay Point 2).")
            # The await is now valid
            try:
                await Actor.push_actor_event( 
                    event_name='llm-analysis-tokens-used',
                    event_data={'value': tokens} 
                )
            except:
                pass 
                
        # Parse and clean the structured JSON result
        parsed = json.loads(output_text)
        
        # Ensure 'key_entities' is handled as a list
        entities = parsed.get("key_entities")
        if not isinstance(entities, list):
             entities = [str(entities)] if entities else []
             
        # Ensure category and sentiment are clean strings
        category = str(parsed.get("category")).strip() if parsed.get("category") else "N/A"
        sentiment = str(parsed.get("sentiment")).strip() if parsed.get("sentiment") else "N/A"

        # Validate sentiment against allowed list
        if sentiment not in sentiment_options:
            sentiment = "Neutral"

        return {
            "sentiment": sentiment,
            "category": category,
            "key_entities": entities
        }

    except Exception as e:
        Actor.log.warning(f"Combined LLM analysis failed: {e}")
        return {"sentiment": "Error", "category": "Error", "key_entities": []}