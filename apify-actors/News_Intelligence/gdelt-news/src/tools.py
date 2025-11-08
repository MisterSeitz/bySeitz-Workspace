import feedparser
import re
import os 
import httpx 
from typing import List, Tuple, Dict, Any, Optional
from apify import Actor
from apify_client import ApifyClient
from openai import OpenAI
from models import DatasetRecord, InputConfig 
import json
import asyncio
from datetime import datetime, timezone
from collections import Counter
from dateutil.parser import parse as date_parse # For flexible date parsing

# Initialize Apify Client
def init_apify_client() -> ApifyClient:
    """Initializes the Apify client."""
    return ApifyClient()

# Initialize OpenAI
def init_openai() -> OpenAI:
    """Initializes the OpenAI client."""
    return OpenAI()

# Global categories for the model to choose from (Cybersecurity focused)
CATEGORIES = [
    "Vulnerability/CVE", "Malware/Ransomware", "Policy/Compliance",
    "Data Breach/Hack", "Threat Intelligence", "Cloud Security",
    "IoT/Hardware", "General InfoSec"
]

def fetch_rss_feeds(source: str, custom_url: str = None, max_articles: int = 20) -> List[dict]:
    """Fetch and parse RSS feed entries for the selected news sources (Cybersecurity News Feeds)."""
    feed_map = {
        "the-hacker-news": "https://feeds.feedburner.com/TheHackersNews",
        "custom": custom_url
    }
    urls = []
    if source == "custom" and custom_url:
        urls.append(custom_url)
    elif source == "all":
        urls = [url for key, url in feed_map.items() if key != "custom" and url is not None]
    else:
        selected = feed_map.get(source)
        if selected:
            urls.append(selected)

    articles = []
    
    if urls and not os.getenv("IS_GDELT_ENRICHMENT", False):
        Actor.log.warning("RSS Feed fetching logic is complex and dependent on original models. Returning empty list.")
    
    return []

async def summarize_snippets_with_llm(snippets: str, is_test_mode: bool) -> str:
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE: Bypassing LLM summarization call.")
        return "This is a test summary generated from dummy search snippets about a recent cybersecurity or geopolitical event."

    client = init_openai()
    prompt = f"""
    Based on the following raw search result snippets, synthesize a concise, neutral, one-paragraph summary of the main news event.
    Focus on the core facts and ignore advertisements or irrelevant text.

    Snippets:
    ---
    {snippets}
    ---
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are a news summarization assistant. Your task is to generate a single, coherent paragraph summarizing the provided search result snippets."},
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

async def extract_most_common_date_from_google(query: str, is_test_mode: bool) -> Optional[str]:
    """
    Performs a Google search, extracts dates from the results, and returns the most common one.
    It prioritizes structured metadata but falls back to parsing snippets.
    """
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE: Bypassing Google Search for date extraction.")
        return datetime.now(timezone.utc).isoformat()

    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        Actor.log.error("Google API Key or CSE ID not set; cannot perform date extraction.")
        return None

    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {'key': api_key, 'cx': cse_id, 'q': query, 'num': 10}
    
    dates_found = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(search_url, params=params)
            response.raise_for_status()
            search_results = response.json()

        items = search_results.get("items", [])
        if not items:
            return None

        for item in items:
            date_str = None
            # 1. Prioritize structured data (pagemap metadata)
            if 'pagemap' in item and 'metatags' in item['pagemap']:
                for tag in item['pagemap']['metatags']:
                    if 'article:published_time' in tag:
                        date_str = tag.get('article:published_time')
                        break
                    elif 'og:published_time' in tag:
                        date_str = tag.get('og:published_time')
                        break
            
            # 2. Fallback to parsing the snippet text
            if not date_str:
                # Regex for YYYY-MM-DD or common text dates
                match = re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s\d{1,2},\s\d{4}|\d{4}-\d{2}-\d{2}\b', item.get('snippet', ''))
                if match:
                    date_str = match.group(0)

            # 3. Parse the string into a datetime object
            if date_str:
                try:
                    # Use dateutil.parser to handle various formats
                    parsed_date = date_parse(date_str).replace(tzinfo=timezone.utc)
                    # Normalize to just the date part for accurate counting
                    dates_found.append(parsed_date.strftime('%Y-%m-%d'))
                except (ValueError, TypeError):
                    continue # Ignore strings that can't be parsed

        if not dates_found:
            return None

        # 4. Find the most common date
        most_common_date_str = Counter(dates_found).most_common(1)[0][0]
        # Return it in full ISO 8601 format for consistency
        return datetime.strptime(most_common_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc).isoformat()

    except Exception as e:
        Actor.log.warning(f"An error occurred during Google date extraction: {e}")
        return None

async def fetch_summary_from_google(query: str, is_test_mode: bool) -> str:
    """
    Runs a Google Search via API, collects snippets, and uses an LLM to generate a summary.
    Implements retry logic for 403 errors to handle rate limits/intermittent service blocking.
    """
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE ENABLED. Bypassing Google Search API call.")
        return await summarize_snippets_with_llm("", is_test_mode=True)

    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        Actor.log.error("Google API Key or CSE ID is not set in environment variables. Aborting search.")
        return ""

    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': cse_id,
        'q': query,
        'num': 5
    }
    
    MAX_RETRIES = 3
    
    for attempt in range(MAX_RETRIES):
        Actor.log.info(f"Searching Google via API for: {query[:60]}... (Attempt {attempt + 1}/{MAX_RETRIES})")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(search_url, params=params)
                
                # Check for 403 (Forbidden) error specifically
                if response.status_code == 403:
                    if attempt < MAX_RETRIES - 1:
                        # Exponential backoff: 2s, 4s, 8s delay
                        delay = 2 ** (attempt + 1)
                        Actor.log.warning(f"Google Search API blocked (403). Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        continue  # Go to next retry attempt
                    else:
                        Actor.log.error(f"Google Search API blocked (403) after {MAX_RETRIES} attempts. Giving up on this article.")
                        return ""
                
                response.raise_for_status() # Raise exception for other bad status codes (4xx, 5xx)
                
                search_results = response.json()

            items = search_results.get("items", [])
            if not items:
                Actor.log.warning("Google Search API returned no items.")
                return ""

            snippets = "\n".join([f"- {item.get('snippet', '')}" for item in items])
            Actor.log.info(f"Collected {len(items)} snippets from Google Search.")

            return await summarize_snippets_with_llm(snippets, is_test_mode=False)

        except httpx.HTTPStatusError as e:
            Actor.log.error(f"Google Search API request failed with status {e.response.status_code}: {e.response.text}")
            return ""
        except Exception as e:
            Actor.log.error(f"An unexpected error occurred during Google Search API call: {e}")
            return ""

    return ""

async def analyze_article_summary(summary: str, is_test_mode: bool) -> Dict[str, Any]:
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE: Bypassing LLM analysis (Pay Point 2 cost skipped).")
        return { "sentiment": "High Risk (TEST)", "category": "Threat Intelligence (TEST)", "key_entities": ["Google", "OpenAI", "Geopolitical Group X"] }

    client = init_openai()
    if not summary or len(summary) < 20:
        Actor.log.warning("Summary too short for analysis. Skipping LLM call.")
        return {"sentiment": "N/A", "category": "N/A", "key_entities": []}

    sentiment_options = ["High Risk", "Medium Risk", "Low Risk/Informational"]
    category_list_str = ", ".join(CATEGORIES)
    prompt = f"""
    Analyze the following Cybersecurity/Geopolitical news summary: "{summary}"

    Based ONLY on the summary, provide a structured JSON output with the following analysis:
    1.  **sentiment**: The overall risk/impact level. Must be one of: {', '.join(sentiment_options)}.
    2.  **category**: The single best thematic category from this list: {category_list_str}.
    3.  **key_entities**: A list of up to 3 key companies, groups, or vulnerabilities (e.g., CVE-XXXX, APT42, Microsoft, Russia, China) explicitly named. If none are found, use an empty list: [].

    Your entire output MUST be a single, valid JSON object matching the requested schema.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are a professional news analyst. You MUST return a single valid JSON object with keys: 'sentiment', 'category', and 'key_entities'. DO NOT include any other text or markdown outside of the JSON object."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        output_text = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens
        if tokens > 0:
            Actor.log.info(f"Reporting {tokens} tokens used for combined analysis.")
            try:
                Actor.push_actor_event( event_name='llm-analysis-tokens-used', event_data={'value': tokens} )
            except:
                pass
        
        parsed = json.loads(output_text)
        entities = parsed.get("key_entities", [])
        if not isinstance(entities, list):
             entities = [str(entities)] if entities else []
        category = str(parsed.get("category", "N/A")).strip()
        sentiment = str(parsed.get("sentiment", "N/A")).strip()
        if sentiment not in sentiment_options:
            sentiment = "Low Risk/Informational"
            
        return { "sentiment": sentiment, "category": category, "key_entities": entities }
    
    except Exception as e:
        Actor.log.warning(f"Combined LLM analysis failed: {e}")
        return {"sentiment": "Error", "category": "Error", "key_entities": []}