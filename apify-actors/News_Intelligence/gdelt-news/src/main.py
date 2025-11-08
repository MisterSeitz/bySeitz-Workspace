import asyncio
from apify import Actor
from datetime import datetime, timezone
import urllib.parse
import json
import aiohttp 
import os
import sys

# Add src/ to path for absolute imports to work when run via python src/main.py
sys.path.append(os.path.dirname(__file__)) 

# Absolute imports for internal modules
from models import InputConfig, DatasetRecord
from tools import fetch_summary_from_google, analyze_article_summary, extract_most_common_date_from_google
from typing import List

# Define the base URL for the GDELT 2.0 DOC API
GDELT_API_BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

## ---------------------------
## GDELT URL and Fetching Utilities
## ---------------------------

def format_datetime(dt_str: str, default_ts: str = "000000") -> str | None:
    """
    Formats a date string into GDELT's YYYYMMDDHHMMSS format.
    Handles YYYYMMDD and YYYY-MM-DD inputs by padding time.
    """
    if not dt_str:
        return None
    dt_str = str(dt_str).strip()
    if len(dt_str) == 14 and dt_str.isdigit():
        return dt_str
    
    try:
        if len(dt_str) == 8 and dt_str.isdigit(): # YYYYMMDD
            return f"{dt_str}{default_ts}"
        elif len(dt_str) == 10 and '-' in dt_str: # YYYY-MM-DD
            dt_obj = datetime.strptime(dt_str, '%Y-%m-%d')
            return dt_obj.strftime('%Y%m%d') + default_ts
    except ValueError:
        pass
        
    return None

def convert_gdelt_date_to_iso(gdelt_date: str) -> str:
    """
    Converts GDELT's YYYYMMDDHHMMSS format to a timezone-aware ISO 8601 string.
    """
    if gdelt_date and len(gdelt_date) == 14 and gdelt_date.isdigit():
        try:
            # Parse GDELT format to a naive datetime object
            dt_obj = datetime.strptime(gdelt_date, '%Y%m%d%H%M%S')
            # Make the datetime object explicitly UTC-aware (GDELT data is in UTC)
            utc_aware_dt = dt_obj.replace(tzinfo=timezone.utc)
            # Convert to ISO 8601 format (e.g., 2025-10-16T09:00:00+00:00)
            return utc_aware_dt.isoformat()
        except ValueError:
            return "N/A"
    return "N/A"

def build_gdelt_url(input_data: dict) -> str:
    """
    Constructs the GDELT API URL from the actor's input data.
    """
    raw_query = input_data['query']
    final_query_parts = []
    
    # Wrap multi-term queries in parentheses for safety
    if 'OR' in raw_query or 'AND' in raw_query:
        if not (raw_query.startswith('(') and raw_query.endswith(')')):
            final_query_parts.append(f"({raw_query})")
        else:
            final_query_parts.append(raw_query)
    else:
        final_query_parts.append(raw_query)

    source_lang = input_data.get('source_lang')
    if source_lang:
        final_query_parts.append(f"sourcelang:{source_lang}")

    final_gdelt_query = ' '.join(final_query_parts)

    params = {
        'mode': 'artlist', 
        'format': 'json',   
        'query': final_gdelt_query 
    }

    if input_data.get('max_records_limit'):
        params['maxrecords'] = input_data['max_records_limit']
    
    if input_data.get('sort_by'):
        params['sort'] = input_data['sort_by']

    # Handle time range (relative offset takes precedence over absolute dates)
    if input_data.get('timespan_offset'):
        params['timespan'] = input_data['timespan_offset']
    else:
        start_dt = format_datetime(input_data.get('start_datetime'), '000000')
        end_dt = format_datetime(input_data.get('end_datetime'), '235959')
        if start_dt:
            params['startdatetime'] = start_dt
        if end_dt:
            params['enddatetime'] = end_dt

    return f"{GDELT_API_BASE_URL}?{urllib.parse.urlencode(params)}"

async def fetch_gdelt_articles(gdelt_url: str) -> List[dict]:
    """
    Fetches raw article data from the GDELT API with a timeout and robust error handling.
    """
    timeout = aiohttp.ClientTimeout(total=120)  # 2-minute total timeout
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(gdelt_url) as gdelt_response:
                gdelt_response.raise_for_status()
                try:
                    # Use content_type=None to handle potential GDELT API header issues
                    gdelt_data = await gdelt_response.json(content_type=None)
                except json.JSONDecodeError:
                    response_text = await gdelt_response.text()
                    Actor.log.error(f"GDELT API returned a non-JSON response. Response text: {response_text[:500]}")
                    return []
                
                if gdelt_data and gdelt_data.get('error'):
                    Actor.log.error(f"GDELT API returned a known error: {gdelt_data.get('error')}")
                    return []
                
                return gdelt_data.get('articles', []) if gdelt_data else []

    except asyncio.TimeoutError:
        Actor.log.error("GDELT API request timed out after 120 seconds.")
        return []
    except aiohttp.ClientError as e:
        Actor.log.error(f"An HTTP error occurred while fetching from GDELT: {e}")
        return []

## ---------------------------
## Main Actor Execution
## ---------------------------

async def main():
    """Main entrypoint for the GDELT Data Enrichment Actor."""
    
    async with Actor:
        Actor.log.info("🚀 Starting GDELT Data Enrichment Pipeline...")
        
        try:
            input_data = await Actor.get_input() or {}
            
            # Load and validate input using the Pydantic model
            config = InputConfig(**input_data)
            Actor.log.info(f"Loaded config: {config.model_dump_json(indent=2)}")

            # Note: API keys are now read directly from secret environment variables by the tools.py module.
            # We no longer set them here from the input config.
            
            if config.runTestMode:
                Actor.log.warning("!!! ADMIN TEST MODE ACTIVE: Bypassing ALL EXTERNAL API costs. !!!")

            # 1. RETRIEVE GDELT Data
            gdelt_url = build_gdelt_url(input_data)
            Actor.log.info(f"GDELT API URL: {gdelt_url}")
            
            gdelt_articles = await fetch_gdelt_articles(gdelt_url)
            
            if not gdelt_articles:
                Actor.log.info("No articles retrieved from GDELT data source. Exiting.")
                return

            Actor.log.info(f"Retrieved {len(gdelt_articles)} GDELT records for enrichment.")
            
            processed_count = 0
            total_articles = len(gdelt_articles)
            
            # 2. ENRICHMENT LOOP
            for article_data in gdelt_articles:
                processed_count += 1
                
                url = article_data.get("url", "N/A")
                title = article_data.get("title", "Unknown Title")
                
                # Always derive the source from the URL for consistency and accuracy.
                source = "N/A" 
                try:
                    parsed_url = urllib.parse.urlparse(url)
                    if parsed_url.netloc:
                        source = parsed_url.netloc.replace('www.', '')
                except Exception as e:
                    Actor.log.warning(f"Could not parse source from URL '{url}': {e}")
                
                query_for_enrichment = f"{title} {source}"

                # --- Date Extraction with Fallback ---
                published = "N/A"
                # Plan A: Try GDELT's 'date' or 'seendate' fields
                raw_gdelt_date = article_data.get("date") or article_data.get("seendate")
                if raw_gdelt_date:
                    cleaned_date = str(raw_gdelt_date).replace('T', '').replace('Z', '')
                    iso_date = convert_gdelt_date_to_iso(cleaned_date)
                    if iso_date != "N/A":
                        published = iso_date

                # Plan B: If GDELT date fails, use Google Search as a fallback
                if published == "N/A":
                    Actor.log.info(f"GDELT date missing for '{title[:30]}...'. Searching Google for a fallback date.")
                    google_date = await extract_most_common_date_from_google(query_for_enrichment, config.runTestMode)
                    if google_date:
                        published = google_date
                        Actor.log.info(f"Found fallback date from Google: {published}")
                    else:
                        Actor.log.warning(f"Could not find a valid date from Google for '{title[:30]}...'.")

                # --- Main Enrichment Logic ---
                Actor.log.info(f"Processing article {processed_count}/{total_articles}: {title[:50]}...")
                
                ai_overview = await fetch_summary_from_google(query_for_enrichment, config.runTestMode)
                
                summary_text = ai_overview or article_data.get('snippet', 'No summary available.')
                article_sentiment, article_category, article_entities = "N/A", "N/A", []

                if ai_overview:
                    analysis_results = await analyze_article_summary(ai_overview, config.runTestMode)
                    article_sentiment = analysis_results.get("sentiment")
                    article_category = analysis_results.get("category")
                    article_entities = analysis_results.get("key_entities")
                else:
                    Actor.log.warning(f"Failed to get AI Overview for '{title[:30]}...', skipping LLM analysis.")

                # --- Save Enriched Record ---
                dataset_record = DatasetRecord(
                    source=source,
                    title=title,
                    url=url,
                    published=published,
                    summary=summary_text,
                    sentiment=article_sentiment,
                    category=article_category,
                    key_entities=article_entities
                ).model_dump()

                await Actor.push_data([dataset_record])
                Actor.log.info(f"Pushed ENRICHED record for '{title[:50]}...' to dataset.")

            Actor.log.info("🎯 GDELT Data Enrichment Pipeline completed successfully!")
            
        except Exception as e:
            Actor.log.exception(f"An unexpected error occurred: {e}")
            await Actor.fail()

if __name__ == "__main__":
    asyncio.run(main())