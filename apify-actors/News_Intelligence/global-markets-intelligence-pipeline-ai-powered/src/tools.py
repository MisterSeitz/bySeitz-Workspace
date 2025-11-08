import feedparser
import re
from typing import List, Tuple, Dict, Any, Union
from apify import Actor
from google import genai
from google.genai import types
from .models import Article
import json
from json.decoder import JSONDecodeError
from collections import deque
import requests
import asyncio
from urllib.parse import urlparse
import urllib.parse
import os
from datetime import datetime, timedelta


# Initialize Gemini client
def init_gemini() -> genai.Client:
    """Initializes the Google Gemini client using the GEMINI_API_KEY environment variable."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        Actor.log.error("GEMINI_API_KEY environment variable not set. Cannot initialize Gemini client.")
        raise ValueError("GEMINI_API_KEY environment variable is missing.")
    return genai.Client(api_key=api_key)


# Global categories for the model to choose from
CATEGORIES = [
    "Monetary Policy", "Trade/Tariffs", "Market Data/Indices",
    "Corporate M&A", "Industry Regulation", "Technology/FinTech",
    "Commodities/Energy", "Geopolitical Risk"
]

# Categorized Feed Map
CATEGORIZED_FEEDS = {
    "World/General News": [
        "http://feeds.bbci.co.uk/news/world/rss.xml", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.reuters.com/arc/outboundfeeds/world-news/?outputType=xml", "https://www.economist.com/latest/rss.xml",
        "https://www.politico.com/rss/politicopulse.xml", "https://www.axios.com/rss/feed/all",
        "https://www.npr.org/rss/rss.php?id=100", "https://www.theatlantic.com/feed/all/",
        "https://www.investing.com/rss/news.rss", "https://www.investing.com/rss/news_1060.rss",
        "https://www.investing.com/rss/news_462.rss", "https://www.investing.com/rss/news_290.rss",
    ],
    "Technology/FinTech": [
        "https://www.nytimes.com/svc/collections/v1/publish/https://www.nytimes.com/section/technology/rss.xml",
        "https://www.bbc.co.uk/news/technology/rss.xml", "https://www.reuters.com/arc/outboundfeeds/technology-news/?outputType=xml",
        "https://techcrunch.com/feed/", "https://www.zdnet.com/topic/technology/rss.xml"
    ],
    "Financial Stability": [
        "https://www.fsb.org/wordpress/content_type/evaluations/feed/", "https://www.fsb.org/wordpress/content_type/peer-review-reports/feed/",
        "https://www.fsb.org/wordpress/content_type/policy-documents/feed/", "https://www.fsb.org/wordpress/content_type/reports-to-the-g20/feed/",
        "https://www.fsb.org/wordpress/content_type/announcements/feed/", "https://www.fsb.org/wordpress/content_type/progress-reports/feed/",
        "https://www.wsj.com/xml/rss/3_7014.xml", "https://www.ft.com/rss/world/economy",
        "https://www.investing.com/rss/bonds.rss", "https://www.investing.com/rss/forex.rss", "https://www.investing.com/rss/news_14.rss",
    ],
    "Index/Market Data": [
        "https://www.wsj.com/xml/rss/3_7014.xml", "https://feeds.bloomberg.com/business/news.rss",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html", "https://hbr.org/feed",
        "https://www.investing.com/rss/market_overview.rss", "https://www.investing.com/rss/market_overview_Technical.rss",
        "https://www.investing.com/rss/stock.rss", "https://www.investing.com/rss/stock_Technical.rss",
        "https://www.investing.com/rss/stock_Fundamental.rss", "https://www.investing.com/rss/stock_Indices.rss",
        "https://www.investing.com/rss/stock_ETFs.rss", "https://www.investing.com/rss/stock_Options.rss",
        "https://www.investing.com/rss/news_25.rss", "https://www.investing.com/rss/news_356.rss", "https://www.investing.com/rss/320.rss",
    ],
    "Monetary Policy": [
        "https://www.ft.com/rss/world/economy", "https://feeds.bloomberg.com/business/news.rss",
        "https://www.fsb.org/wordpress/content_type/speeches/feed/", "https://www.investing.com/rss/central_banks.rss",
        "https://www.investing.com/rss/news_95.rss",
    ],
    "Economics/Research": [
        "https://hbr.org/feed", "https://feeds.bloomberg.com/business/news.rss",
        "https://www.investing.com/rss/market_overview_Fundamental.rss", "https://www.investing.com/rss/forex_Fundamental.rss",
        "https://www.investing.com/rss/stock_Fundamental.rss", "https://www.investing.com/rss/commodities_Fundamental.rss",
        "https://www.investing.com/rss/bonds_Fundamental.rss",
    ],
    "Commodities/Crypto": [
        "https://www.cnbc.com/id/100003114/device/rss/rss.html", "https://www.investing.com/rss/commodities.rss",
        "https://www.investing.com/rss/commodities_Metals.rss", "https://www.investing.com/rss/commodities_Energy.rss",
        "https://www.investing.com/rss/commodities_Agriculture.rss", "https://www.investing.com/rss/302.rss",
        "https://www.investing.com/rss/news_301.rss", "https://www.investing.com/rss/news_11.rss",
    ]
}


def fetch_rss_feeds(source: str, custom_url: str = None, max_articles: int = 20) -> List[Article]:
    """Fetch and parse RSS feed entries."""
    if source == "Alpha Vantage News":
        Actor.log.info("Dedicated Alpha Vantage mode selected. Skipping traditional RSS feed fetch.")
        return []

    urls = []
    category_name = source
    if source == "custom" and custom_url:
        urls = [custom_url]
    elif source == "all":
        urls = list(set(url for category_list in CATEGORIZED_FEEDS.values() for url in category_list))
    elif source in CATEGORIZED_FEEDS:
        urls = CATEGORIZED_FEEDS[source]
    else:
        Actor.log.error(f"Invalid source or category selected: {source}")
        return []

    Actor.log.info(f"Fetching articles from category: {category_name} ({len(urls)} feeds)")

    parsed_feeds = []
    for feed_url in urls:
        try:
            parsed = feedparser.parse(feed_url)
            if parsed.entries:
                source_title = parsed.feed.get("title", f"Unknown ({feed_url})")
                parsed_feeds.append((iter(parsed.entries), source_title))
        except Exception as e:
            Actor.log.warning(f"Failed to parse feed {feed_url}: {e}")

    if not parsed_feeds:
        return []

    articles = []
    feed_queue = deque(parsed_feeds)
    while len(articles) < max_articles and feed_queue:
        entry_iterator, source_title = feed_queue.popleft()
        try:
            entry = next(entry_iterator)
            article_item = Article(
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                source=source_title,
                published=entry.get("published"),
                summary=entry.get("summary"),
            )
            articles.append(article_item)
            feed_queue.append((entry_iterator, source_title))
        except StopIteration:
            Actor.log.info(f"Source exhausted: {source_title}")
        except Exception as e:
            Actor.log.warning(f"Error reading entry from {source_title}: {e}. Skipping source.")

    Actor.log.info(f"Collected a total of {len(articles)} articles from RSS feeds.")
    return articles


async def fetch_alpha_vantage_articles(source_topic: str, max_articles: int, is_test_mode: bool) -> List[Article]:
    """Fetches latest financial news directly from the Alpha Vantage NEWS_SENTIMENT API."""
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE ENABLED. Returning Alpha Vantage dummy articles.")
        return [
            Article(title="TEST: Fed Signals Rate Cut is Imminent", url="https://test.av.com/fed-cut", source="Alpha Vantage", summary="Fed decision signals rate change"),
            Article(title="TEST: Apple Stock Jumps on New AI Chip Announcement", url="https://test.av.com/apple-chip", source="Alpha Vantage", summary="Apple news causes stock jump")
        ]

    api_key = os.getenv("ALPHA_VANTAGE_API")
    if not api_key:
        Actor.log.error("ALPHA_VANTAGE_API environment variable not set. Cannot fetch AV news.")
        return []

    av_topic_map = {
        "Monetary Policy": "economy_monetary", "Index/Market Data": "financial_markets",
        "Financial Stability": "finance", "Economics/Research": "economy_macro",
        "Technology/FinTech": "technology", "Commodities/Crypto": "energy_transportation",
        "World/General News": "economy_macro", "Alpha Vantage News": "financial_markets,economy_monetary,technology",
        "all": "financial_markets,economy_monetary,technology"
    }
    av_topic = av_topic_map.get(source_topic, "financial_markets")
    
    AV_API_URL = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT", "topics": av_topic,
        "time_from": (datetime.utcnow() - timedelta(days=7)).strftime("%Y%m%dT%H%M"),
        "limit": max_articles, "sort": "RELEVANCE", "apikey": api_key
    }
    
    Actor.log.info(f"Fetching Alpha Vantage articles for topic: {av_topic}")
    try:
        response = requests.get(AV_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "Error Message" in data:
            Actor.log.error(f"Alpha Vantage API returned error: {data['Error Message']}")
            return []
        
        articles = []
        for item in data.get("feed", []):
            articles.append(Article(
                title=item.get("title", "No Title"), url=item.get("url", ""),
                source=item.get("source", "Alpha Vantage"), published=item.get("time_published"),
                summary=item.get("summary")
            ))
        
        Actor.log.info(f"Collected {len(articles)} articles directly from Alpha Vantage.")
        return articles
    except requests.exceptions.RequestException as e:
        Actor.log.error(f"Alpha Vantage API request failed: {e}")
        return []


async def analyze_article_summary(article: Article, is_test_mode: bool) -> Dict[str, Any]:
    """
    Performs LLM analysis using Google Programmable Search for grounding, then Gemini for structured output.
    """
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE: Bypassing external APIs for analysis.")
        return {"sentiment": "Neutral (TEST)", "category": "Market Data/Indices (TEST)", "key_entities": ["Powell", "Interest Rates"], "gdelt_tone": 0.0}

    # --- STEP 1: Grounding with Google Programmable Search ---
    search_snippets = ""
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    search_query = f"{article.title} {article.source}"

    if not api_key or not cse_id:
        Actor.log.warning("Google API Key or CSE ID not set in environment variables. Skipping search grounding.")
    else:
        Actor.log.info(f"Searching Google for grounding context: {search_query[:70]}...")
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {'key': api_key, 'cx': cse_id, 'q': search_query, 'num': 5}
        
        try:
            # Using requests for this synchronous call
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            search_results = response.json()
            items = search_results.get("items", [])
            if items:
                search_snippets = "\n".join([f"- {item.get('snippet', '')}" for item in items])
                Actor.log.info(f"Collected {len(items)} snippets from Google Search for grounding.")
        except requests.RequestException as e:
            Actor.log.warning(f"Google Search API call failed: {e}")

    # --- STEP 2: Structure Extraction with Gemini ---
    try:
        client = init_gemini()
    except ValueError:
        return {"sentiment": "Error", "category": "Error", "key_entities": [], "gdelt_tone": None}

    sentiment_options = ["Positive", "Neutral", "Negative"]
    category_list_str = ", ".join(CATEGORIES)
    
    # Use the collected snippets for better context, or fall back to the article's own summary.
    context_for_analysis = search_snippets if search_snippets else (article.summary or article.title)

    extraction_prompt = f"""
    Analyze the following text derived from a real-time market search or article summary.
    Based ONLY on the text provided below, generate a structured JSON object.

    TEXT: "{context_for_analysis}"

    JSON Schema:
    1.  **sentiment**: The overall market mood/tone (Positive, Neutral, or Negative).
    2.  **category**: The single best thematic category from this list: {category_list_str}.
    3.  **key_entities**: A list of up to 3 key companies, people, or macroeconomic terms (e.g., 'Inflation', 'ECB', 'TSLA') mentioned.
    4.  **numeric_score**: A single float between -10.0 (very negative) and +10.0 (very positive) reflecting market impact.

    Your entire output MUST be a single, valid JSON object.
    """
    
    Actor.log.info("Gemini: Extracting structured analysis from provided context.")
    try:
        extraction_response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[{"role": "user", "parts": [{"text": extraction_prompt}]}],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        parsed = json.loads(extraction_response.text.strip())
        sentiment = str(parsed.get("sentiment", "Neutral")).strip()
        
        return {
            "sentiment": sentiment if sentiment in sentiment_options else "Neutral",
            "category": str(parsed.get("category", "N/A")).strip(),
            "key_entities": [str(e).strip() for e in parsed.get("key_entities", [])][:3],
            "gdelt_tone": float(parsed.get("numeric_score", 0.0))
        }
    except Exception as e:
        Actor.log.warning(f"Gemini structure extraction failed: {e}")
        return {"sentiment": "Error", "category": "Error", "key_entities": [], "gdelt_tone": None}


async def generate_llm_summary(article: Article, is_test_mode: bool) -> str:
    """Generates an AI summary for an article using the Gemini LLM."""
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE: Bypassing LLM summarization.")
        return f"TEST MODE SUMMARY: Summary for {article.title}."
        
    content_to_summarize = article.summary if article.summary else f"Title: {article.title}. Source: {article.source}."

    try:
        client = init_gemini()
    except ValueError:
        return "LLM Summary Error: Gemini client initialization failed."
    
    prompt = f"""
    Create a concise, one-paragraph summary of the following news article context. Focus on the main financial, market, or policy implications.
    Article Context: "{content_to_summarize}"
    Your entire output MUST be the summary text ONLY.
    """

    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config=types.GenerateContentConfig(temperature=0.0)
        )
        return response.text.strip()
    except Exception as e:
        Actor.log.warning(f"LLM summarization failed: {e}")
        return f"LLM Summary Error: {article.title}"