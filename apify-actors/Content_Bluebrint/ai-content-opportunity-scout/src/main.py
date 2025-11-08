import asyncio
import logging
import os
import random
from typing import List, Dict, Any

from apify import Actor
from apify_client import ApifyClientAsync

# from google.ads.googleads.client import GoogleAdsClient  # Placeholder if API is integrated later

# -------------------------------------------------------------------
# LOGGING SETUP
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# MOCK GOOGLE ADS KEYWORD LOOKUP
# -------------------------------------------------------------------
async def google_ads_api_keyword_lookup(
    topic: str,
    long_tail_keywords: List[str],
    language_code: str,
    location_ids: List[int]
) -> Dict[str, Any]:
    """Simulates the Google Ads Keyword Planner API call."""
    logger.info(f"[MOCK] Keyword lookup for '{topic}' (Lang: {language_code}, Loc: {location_ids})")

    random.seed(hash(topic))
    base_volume = int(random.gauss(20000, 10000))
    search_volume = max(100, base_volume)
    competition_levels = ["Low", "Medium", "High"]
    competition = random.choice(competition_levels)
    bid_low = round(random.uniform(0.5, 3.0), 2)
    bid_high = round(bid_low + random.uniform(1.0, 5.0), 2)

    long_tail_opportunities = []
    for keyword in long_tail_keywords[:5]:
        lt_volume = max(10, int(search_volume * random.uniform(0.01, 0.2)))
        lt_comp = random.choice(competition_levels)
        lt_bid_low = round(bid_low * random.uniform(0.8, 1.5), 2)
        long_tail_opportunities.append({
            "keyword": keyword,
            "volume": lt_volume,
            "competition": lt_comp,
            "bid_low": lt_bid_low
        })

    await asyncio.sleep(random.uniform(0.1, 0.4))  # Simulate network latency
    return {
        "search_volume": search_volume,
        "competition": competition,
        "top_of_page_bid_low": bid_low,
        "top_of_page_bid_high": bid_high,
        "long_tail_opportunities": long_tail_opportunities,
    }

# -------------------------------------------------------------------
# SCORING AND STRATEGY LOGIC
# -------------------------------------------------------------------
def calculate_ai_cluster_score(
    trend_score: float,
    search_volume: int,
    competition: str,
    max_volume: int,
    topic: str
) -> int:
    """Calculates custom AI Cluster Score (0–100)."""
    trend_factor = trend_score * 2.0
    normalized_volume = (search_volume / max_volume) * 100 if max_volume > 0 else 0
    volume_factor = normalized_volume * 0.3

    comp_map = {"Low": 1, "Medium": 2, "High": 3}
    comp_level = comp_map.get(competition, 2)
    competition_score = 100 - (comp_level * 33.33)
    competition_factor = max(0, competition_score * 0.2)

    ai_keywords = [
        "ai", "artificial intelligence", "tech", "technology", "software",
        "data", "machine learning", "business", "vc", "startup", "ethics",
        "robotics", "regulation"
    ]
    relevance_factor = 30 if any(k in topic.lower() for k in ai_keywords) else 0

    score = trend_factor + volume_factor + competition_factor + relevance_factor
    return int(round(min(100, score)))

def determine_best_strategy(competition: str, ai_cluster_score: int) -> str:
    """Suggests a go-to-market strategy."""
    if ai_cluster_score >= 90 and competition == "Low":
        return "Top Opportunity (High Score, Low Competition, Max Effort)"
    elif ai_cluster_score >= 80 and competition in ["Low", "Medium"]:
        return "Strong Opportunity (High Score, Standard Effort)"
    elif competition == "Low":
        return "Niche Topic (Low Competition, Easy Win)"
    elif competition == "High" and ai_cluster_score >= 70:
        return "High Competition, Worth the Investment"
    return "Standard Opportunity"

def extract_long_tail_keywords(articles: List[Dict[str, Any]]) -> List[str]:
    """Extracts long-tail keywords from nested article entities."""
    keywords = set()
    for article in articles:
        for entity in article.get("key_entities", []):
            if isinstance(entity, str) and len(entity.split()) > 1:
                keywords.add(entity)
    return list(keywords)[:5]

# -------------------------------------------------------------------
# MAIN ACTOR LOGIC
# -------------------------------------------------------------------
async def main():
    async with Actor:
        actor_input: Dict[str, Any] = await Actor.get_input() or {}

        source_dataset_id = actor_input.get("source_dataset_id")
        min_trend_score = actor_input.get("min_trend_score", 7.0)
        language_code = actor_input.get("language_code", "en")
        location_ids = actor_input.get("location_ids", [2840])  # default: United States

        if not source_dataset_id:
            logger.error("❌ Missing 'source_dataset_id' in input. Exiting.")
            return

        token = os.getenv("APIFY_TOKEN")
        client = ApifyClientAsync(token=token)

        # ----------------------------------------------------------
        # 1. Fetch and filter topics
        # ----------------------------------------------------------
        all_topics: List[Dict[str, Any]] = []
        try:
            async for item in client.dataset(source_dataset_id).iterate_items():
                all_topics.append(item)
        except Exception as e:
            logger.error(f"Error reading dataset {source_dataset_id}: {e}")
            return

        filtered = [i for i in all_topics if i.get("trend_score", 0.0) >= min_trend_score]
        if not filtered:
            logger.info(f"No topics found with trend_score >= {min_trend_score}. Nothing to process.")
            return
        logger.info(f"Processing {len(filtered)} high-priority topics.")

        # ----------------------------------------------------------
        # 2. Perform keyword lookups concurrently
        # ----------------------------------------------------------
        tasks = []
        for topic_item in filtered:
            topic = topic_item.get("cluster_topic") or topic_item.get("topic", "Untitled")
            long_tail = extract_long_tail_keywords(topic_item.get("articles", []))
            tasks.append(google_ads_api_keyword_lookup(topic, long_tail, language_code, location_ids))

        keyword_results = await asyncio.gather(*tasks)

        # ----------------------------------------------------------
        # 3. Merge keyword data and compute scores
        # ----------------------------------------------------------
        enriched = []
        max_search_volume = max([r["search_volume"] for r in keyword_results], default=1)

        for topic_item, keyword_data in zip(filtered, keyword_results):
            merged = {**topic_item, **keyword_data}
            merged["ai_cluster_score"] = calculate_ai_cluster_score(
                merged["trend_score"],
                merged["search_volume"],
                merged["competition"],
                max_search_volume,
                merged.get("cluster_topic") or merged.get("topic", "Untitled")
            )
            merged["best_strategy"] = determine_best_strategy(
                merged["competition"],
                merged["ai_cluster_score"]
            )
            enriched.append(merged)

        # ----------------------------------------------------------
        # 4. Output to default dataset
        # ----------------------------------------------------------
        if enriched:
            await Actor.push_data(enriched)
            logger.info(f"✅ Successfully output {len(enriched)} keyword opportunities.")
        else:
            logger.info("No enriched data to output — finishing run.")

# -------------------------------------------------------------------
# LOCAL TEST ENTRYPOINT
# -------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Running AI Opportunity Scout locally (mock mode)...")
    asyncio.run(main())