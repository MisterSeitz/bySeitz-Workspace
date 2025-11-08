import asyncio
import re
import os
import json
import aiohttp
import tldextract
from datetime import datetime, timezone
from dateutil import parser
from apify import Actor
from apify_client import ApifyClient
from collections import defaultdict

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

def normalize_title(title: str) -> str:
    """Cleans a title string for use in an ID."""
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', '', title.lower())).strip()

def get_country_from_url(url: str) -> str | None:
    """Extracts the country name from a URL's TLD, if available."""
    cc_to_country = {
        "za": "South Africa", "uk": "United Kingdom", "us": "United States",
        "ca": "Canada", "au": "Australia", "de": "Germany", "jp": "Japan",
        "cn": "China", "in": "India", "br": "Brazil", "ng": "Nigeria",
        "ke": "Kenya"
    }
    try:
        extracted = tldextract.extract(url)
        tld = extracted.suffix.split('.')[-1]
        return cc_to_country.get(tld)
    except Exception:
        return None

def is_title_valid(title: str) -> bool:
    """Checks if a title is present and not a placeholder."""
    if not title or not isinstance(title, str) or not title.strip():
        return False
    placeholder_phrases = ["untitled", "no title"]
    return not any(phrase in title.lower() for phrase in placeholder_phrases)

def is_summary_valid(summary: str) -> bool:
    """Checks if a summary is present and not a placeholder."""
    if not summary or not isinstance(summary, str) or not summary.strip():
        return False
    placeholder_phrases = ["no summary", "summary not available"]
    return not any(phrase in summary.lower() for phrase in placeholder_phrases)

async def get_google_trend_data(keyword: str):
    """Fetch average interest score and related queries from Google Trends."""
    if not PYTRENDS_AVAILABLE:
        return {"google_trend_score": 0, "related_queries": []}
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        pytrends.build_payload([keyword], timeframe='now 7-d')
        data = pytrends.interest_over_time()
        avg_score = int(data[keyword].mean()) if not data.empty else 0
        related = pytrends.related_queries().get(keyword, {}).get('top')
        related_list = related['query'].head(5).tolist() if related is not None else []
        return {"google_trend_score": avg_score, "related_queries": related_list}
    except Exception as e:
        Actor.log.warning(f"Google Trends fetch failed for '{keyword}': {e}")
        return {"google_trend_score": 0, "related_queries": []}

def _count_and_enrich_entities(article_list: list, entity_list: list) -> list:
    """Counts entity mentions in articles and enriches the entity list."""
    if not entity_list or not isinstance(entity_list, list):
        return []
        
    full_text = " ".join([f"{a.get('title', '')} {a.get('summary', '')}" for a in article_list]).lower()
    
    enriched_entities = []
    for entity in entity_list:
        if isinstance(entity, dict) and 'name' in entity:
            name = entity.get('name')
            # Simple case-insensitive count
            mention_count = full_text.count(name.lower())
            
            # Add the 'mentions' count to the entity object
            entity['mentions'] = mention_count
            enriched_entities.append(entity)
            
    return enriched_entities

async def _llm_multi_cluster_analysis(session: aiohttp.ClientSession, articles: list, category: str, max_clusters: int):
    """Ask the LLM to detect trends and extract categorized named entities."""
    content_for_prompt = "\n".join([f"Title: {a['title']}\nSummary: {a['summary']}" for a in articles[-30:]])
    prompt = f"""
    Analyze the following news content from the '{category}' category.
    Identify up to {max_clusters} distinct emerging trends.
    For each trend, provide a detailed breakdown. Your response MUST be a valid JSON array where each object includes:
    1.  `cluster_topic`: A concise, human-readable label for the trend.
    2.  `trend_score`: A momentum score from 1-100.
    3.  `mentioned_locations`: An array of objects, where each object has `name` (string) and `category` (e.g., "City", "Country").
    4.  `mentioned_people`: An array of objects, where each object has `name` (string) and `category` (e.g., "Politician", "CEO", "Artist").
    5.  `mentioned_organizations`: An array of objects, where each object has `name` (string) and `category` (e.g., "Tech Company", "Government Agency", "NGO").
    6.  `mentioned_products`: An array of objects, where each object has `name` (string) and `category` (e.g., "Software", "Consumer Electronics").
    7.  `mentioned_events`: An array of objects, where each object has `name` (string) and `category` (e.g., "Sporting Event", "Political Summit").

    Content for analysis:
    ---
    {content_for_prompt}
    ---

    Example for one person: "mentioned_people": [{{"name": "Elon Musk", "category": "Business Magnate"}}]
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}", "Content-Type": "application/json"}
    data = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}
    
    try:
        async with session.post(url, headers=headers, json=data) as response:
            response.raise_for_status()
            result = await response.json()
            content_str = result.get("choices", [{}])[0].get("message", {}).get("content", "[]")
            trends = json.loads(content_str)
            
            if isinstance(trends, dict) and 'trends' in trends:
                trends = trends['trends']
            if not isinstance(trends, list):
                trends = [trends]

            outputs = []
            for t in trends:
                t_topic = t.get("cluster_topic")
                if not t_topic or "untitled" in t_topic.lower():
                    Actor.log.warning(f"LLM returned an invalid topic for category '{category}'. Skipping.")
                    continue

                gdata = await get_google_trend_data(t_topic)
                composite_score = int(t.get("trend_score", 50) * 0.7 + gdata["google_trend_score"] * 0.3)
                
                # Count and enrich each entity type
                enriched_locations = _count_and_enrich_entities(articles, t.get("mentioned_locations", []))
                enriched_people = _count_and_enrich_entities(articles, t.get("mentioned_people", []))
                enriched_orgs = _count_and_enrich_entities(articles, t.get("mentioned_organizations", []))
                enriched_products = _count_and_enrich_entities(articles, t.get("mentioned_products", []))
                enriched_events = _count_and_enrich_entities(articles, t.get("mentioned_events", []))

                outputs.append({
                    "cluster_id": f"TREND_{normalize_title(t_topic)[:40].replace(' ', '_').upper()}_{datetime.utcnow().strftime('%Y%m%d')}",
                    "cluster_topic": t_topic,
                    "trend_score": composite_score,
                    "google_trend_score": gdata["google_trend_score"],
                    "related_queries": gdata["related_queries"],
                    "mentioned_locations": enriched_locations,
                    "mentioned_people": enriched_people,
                    "mentioned_organizations": enriched_orgs,
                    "mentioned_products": enriched_products,
                    "mentioned_events": enriched_events,
                    "articles_count": len(articles),
                    "articles": articles
                })
            return outputs
    except Exception as e:
        Actor.log.error(f"LLM multi-trend extraction failed for {category}: {e}")
        return []

async def main():
    async with Actor:
        Actor.log.info("🚀 Starting Topic Trend Aggregator...")
        actor_input = await Actor.get_input() or {}
        news_sources = actor_input.get("news_sources", [])
        max_articles_per_source = actor_input.get("max_articles", 20)
        max_clusters = actor_input.get("max_clusters_per_category", 5)

        if not PYTRENDS_AVAILABLE:
            await Actor.fail(status_message="The 'pytrends' package is missing. Please add it to requirements.txt.")
            return

        apify_token = os.environ.get("APIFY_TOKEN")
        if not apify_token:
            await Actor.fail(status_message="Missing APIFY_TOKEN.")
            return
        apify_client = ApifyClient(apify_token)

        historical_articles_by_category = await Actor.get_value("TREND_STATE") or {}
        dedupe_urls = {a['url'] for arts in historical_articles_by_category.values() for a in arts}
        new_articles = []
        incomplete_runs_tracker = defaultdict(lambda: {"missing_items": 0, "reason": ""})

        for source in news_sources:
            actor_id, category, source_type = source.get("actorId"), source.get("categoryName"), source.get("sourceType")
            if not all([actor_id, category, source_type]):
                continue
            try:
                run = apify_client.actor(actor_id).last_run(status="SUCCEEDED").get()
                if not run or not run.get("defaultDatasetId"):
                    incomplete_runs_tracker[actor_id]["reason"] = "No successful run with a dataset found."
                    continue

                dataset_items = apify_client.dataset(run["defaultDatasetId"]).list_items(limit=max_articles_per_source).items
                for article in dataset_items:
                    title, summary, published_str, url = article.get('title'), article.get('summary'), article.get('published'), article.get('url')

                    if not is_title_valid(title) or not is_summary_valid(summary) or not url or not published_str:
                        incomplete_runs_tracker[actor_id]["missing_items"] += 1
                        incomplete_runs_tracker[actor_id]["reason"] = "Skipped items due to missing/invalid data."
                        continue

                    if url in dedupe_urls:
                        continue
                    
                    dedupe_urls.add(url)
                    new_articles.append({
                        "title": title, "url": url, "published": published_str,
                        "summary": summary, "category": category, "source_actor": actor_id,
                        "source_type": source_type,
                        "source_country": get_country_from_url(url)
                    })
            except Exception as e:
                Actor.log.error(f"Failed fetching from {actor_id}: {e}")
                incomplete_runs_tracker[actor_id]["reason"] = f"An exception occurred: {e}"

        Actor.log.info(f"Fetched {len(new_articles)} new, valid, and unique articles.")

        for a in new_articles:
            historical_articles_by_category.setdefault(a["category"], []).append(a)

        for cat in historical_articles_by_category:
            historical_articles_by_category[cat] = sorted(
                historical_articles_by_category[cat],
                key=lambda x: parser.parse(x['published'], ignoretz=True, default=datetime.min),
                reverse=True
            )[:500]

        results = []
        if os.getenv("OPENAI_API_KEY"):
            async with aiohttp.ClientSession() as session:
                tasks = [
                    _llm_multi_cluster_analysis(session, arts, cat, max_clusters)
                    for cat, arts in historical_articles_by_category.items() if arts
                ]
                batch_results = await asyncio.gather(*tasks)
                results.extend(item for sublist in batch_results for item in sublist)
        else:
            Actor.log.warning("OPENAI_API_KEY missing, skipping analysis.")

        if results:
            await Actor.push_data(results)
        
        if incomplete_runs_tracker:
            metadata_record = {"run_metadata": {"timestamp": datetime.now(timezone.utc).isoformat(), "incomplete_runs": [{"actor_id": k, **v} for k, v in incomplete_runs_tracker.items()]}}
            await Actor.push_data([metadata_record])

        await Actor.set_value("TREND_STATE", historical_articles_by_category)
        Actor.log.info("✅ Aggregator finished successfully.")

if __name__ == "__main__":
    asyncio.run(main())