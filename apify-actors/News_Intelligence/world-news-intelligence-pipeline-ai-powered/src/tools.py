import feedparser
import re
from typing import List, Tuple, Dict, Any, Union
from apify import Actor
from apify_client import ApifyClient
from openai import OpenAI
from .models import RSSFeed, Article, SummaryResult
import json
from collections import deque 


# Initialize Apify Client
def init_apify_client() -> ApifyClient:
    """Initializes the Apify client."""
    return ApifyClient()

# Initialize OpenAI
def init_openai() -> OpenAI:
    """Initializes the OpenAI client."""
    return OpenAI()

# Global categories for the model to choose from (World News focused)
CATEGORIES = [
    "Politics/Government", "Conflict/Security", "Economy/Trade", 
    "Environment/Climate", "Health/Science", "Human Rights/Social Issues", 
    "Technology", "Disaster/Accident"
]

# 💡 NEW: Categorized Feed Map
CATEGORIZED_FEEDS = {
    "Technology": [
        "https://www.nytimes.com/svc/collections/v1/publish/https://www.nytimes.com/section/technology/rss.xml",
        "https://www.bbc.co.uk/news/technology/rss.xml",
        "https://www.reuters.com/arc/outboundfeeds/technology-news/?outputType=xml",
        "https://techcrunch.com/feed/",
        "https://www.zdnet.com/topic/technology/rss.xml"
    ],
    "Business/Finance": [
        "https://www.wsj.com/xml/rss/3_7014.xml",
        "https://feeds.bloomberg.com/business/news.rss",
        "https://www.ft.com/rss/world/economy",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://hbr.org/feed" # Harvard Business Review
    ],
    "World/Politics": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.reuters.com/arc/outboundfeeds/world-news/?outputType=xml",
        "https://www.economist.com/latest/rss.xml",
        "https://www.politico.com/rss/politicopulse.xml"
    ],
    "Health/Science": [
        "https://www.sciencedaily.com/rss/all.xml",
        "https://rss.sciencedaily.com/health_medicine.xml",
        "https://www.newscientist.com/feed/home/",
        "https://www.sciam.com/feed/rss/all/",
        "https://www.nih.gov/feed/health-topics/feed"
    ],
    "Lifestyle/Culture": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml",
        "https://www.theguardian.com/lifeandstyle/rss"
    ],
    "Other": [
        "https://www.axios.com/rss/feed/all",
        "https://www.npr.org/rss/rss.php?id=100", # NPR Top Stories
        "https://www.theatlantic.com/feed/all/"
    ]
}


# -------------------------------
# 1️⃣ Fetch RSS Feeds by Source (Updated to use Categories and Round-Robin)
# -------------------------------
def fetch_rss_feeds(source: str, custom_url: str = None, max_articles: int = 20) -> List[RSSFeed]:
    """
    Fetch and parse RSS feed entries, supporting category selection and enforcing 
    a round-robin article fetching strategy to maximize source diversity.
    """

    urls = []
    
    if source == "custom" and custom_url:
        urls = [custom_url]
        category_name = "Custom"
        source_examples = ["Custom URL"]
    elif source == "all":
        # Combine all URLs from all categories for 'all' mode
        urls = [url for category_list in CATEGORIZED_FEEDS.values() for url in category_list]
        category_name = "All Categories"
        source_examples = ["NYT", "BBC", "WSJ", "Bloomberg", "Economist"]
    elif source in CATEGORIZED_FEEDS:
        urls = CATEGORIZED_FEEDS[source]
        category_name = source
        # Extract source names for logging transparency
        source_examples = [re.search(r'(?:www\.|feeds\.|//)([\w\.]+)', url).group(1).split('.')[-2].capitalize() 
                           for url in urls if re.search(r'(?:www\.|feeds\.|//)([\w\.]+)', url)]
        source_examples = list(set(source_examples))[:3] # Show up to 3 unique examples
    else:
        Actor.log.error(f"Invalid source or category selected: {source}")
        return []

    Actor.log.info(f"Fetching articles from category: {category_name} [Sources: {', '.join(source_examples)}] ({len(urls)} feeds)")

    # 1. Parse all feeds immediately
    parsed_feeds = [] 
    for feed_url in urls:
        try:
            parsed = feedparser.parse(feed_url)
            if parsed.entries:
                source_title = parsed.feed.get("title", f"Unknown ({feed_url})")
                
                # Store the iterator and title
                parsed_feeds.append((iter(parsed.entries), source_title))
            # else: log warning is suppressed here to keep the log clean during normal operation
        except Exception as e:
            Actor.log.warning(f"Failed to parse feed {feed_url}: {e}")
            
    if not parsed_feeds:
        Actor.log.warning(f"No functional feeds found for category: {source}")
        return []

    articles = []
    
    # 2. Implement Round-Robin Collection for Diversity
    feed_queue = deque(parsed_feeds)
    num_sources = len(parsed_feeds)
    
    while len(articles) < max_articles and feed_queue:
        entry_iterator, source_title = feed_queue.popleft()
        
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
            
            # If successful, put the iterator back at the end of the queue for the next round
            feed_queue.append((entry_iterator, source_title))
            
        except StopIteration:
            Actor.log.info(f"Source exhausted: {source_title}")
        except Exception as e:
            Actor.log.warning(f"Error reading entry from {source_title}: {e}. Skipping source.")
            
    Actor.log.info(f"Collected a total of {len(articles)} articles, cycling through {num_sources} sources.")
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
        # World News-specific dummy summary
        return f"TEST MODE SUMMARY: Tensions escalated between {query.split()[0]} and a neighboring state following a border incident. International bodies are calling for immediate diplomatic intervention to prevent a wider conflict in the region."
        

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
    
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE: Bypassing LLM analysis (Pay Point 2 cost skipped).")
        # Return structured dummy data for validation
        return {
            "sentiment": "Negative (TEST)",
            "category": "Conflict/Security (TEST)",
            "key_entities": ["United Nations", "Russia", "Ukraine"]
        }

    client = init_openai()
    
    if not summary or len(summary) < 50:
        Actor.log.warning("Summary too short for analysis. Skipping LLM call (Pay Point 2 skipped).")
        return {"sentiment": "N/A", "category": "N/A", "key_entities": []}

    sentiment_options = ["Positive", "Neutral", "Negative"]
    category_list_str = ", ".join(CATEGORIES)
    
    prompt = f"""
    Analyze the following World News summary: "{summary}"

    Based ONLY on the summary, provide a structured JSON output with the following analysis:
    1.  **sentiment**: The overall mood. Must be one of: {', '.join(sentiment_options)}.
    2.  **category**: The single best thematic category from this list: {category_list_str}.
    3.  **key_entities**: A list of up to 3 key countries, organizations (e.g., UN, NATO), or individuals explicitly named. If none are found, use an empty list: [].

    Your entire output MUST be a single, valid JSON object matching the requested schema.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125", 
            messages=[
                {"role": "system", "content": "You are a professional World News analyst. You MUST return a single valid JSON object with keys: 'sentiment' (string), 'category' (string), and 'key_entities' (list of strings). DO NOT include any other text or markdown outside of the JSON object."},
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
        # 🚨 FIX LINE 300: Ensure the return dictionary is correctly formatted here
        Actor.log.warning(f"Combined LLM analysis failed: {e}")
        return {
            "sentiment": "Error", 
            "category": "Error", 
            "key_entities": []
        }