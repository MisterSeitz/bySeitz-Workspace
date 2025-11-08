from __future__ import annotations
import os
import aiohttp
import asyncio
import hashlib
from urllib.parse import quote_plus
from apify import Actor
from openai import AsyncOpenAI
from datetime import datetime

# --- Constants ---
API_STATE_KEY = "API_USAGE_STATE"
PROCESSED_LINKS_STORE_NAME = "processed-links"
FREE_TIER_DAILY_LIMIT = 200

# --- Environment variables ---
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client (if key exists)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def _get_safe_key(url: str) -> str:
    """Creates a SHA-256 hash of a URL to use as a safe key."""
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


async def fetch_json(session, url):
    """Fetch a URL and return parsed JSON (or None if failed)."""
    try:
        async with session.get(url, timeout=30) as response:
            if response.status != 200:
                Actor.log.warning(f"Request failed ({response.status}) for URL: {url}")
                return None, False  # Data, Success
            return await response.json(), True
    except Exception as e:
        Actor.log.warning(f"Failed to fetch data from {url}: {e}")
        return None, False


async def summarize_with_openai(title: str, description: str) -> str | None:
    """Summarize article text using OpenAI (new SDK syntax)."""
    if not openai_client:
        return None

    try:
        Actor.log.info(f"Summarizing: {title[:60]}...")
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the following article briefly in one or two sentences.",
                },
                {
                    "role": "user",
                    "content": f"Title: {title}\n\nContent: {description}",
                },
            ],
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        Actor.log.warning(f"OpenAI summarization failed: {e}")
        return None


async def main() -> None:
    async with Actor:
        input_data = await Actor.get_input() or {}

        # --- Input parameters ---
        keywords = input_data.get("keywords", "")
        category = input_data.get("category", "world")
        country = input_data.get("country", "za")
        language = input_data.get("language", "en")
        max_articles = int(input_data.get("maxArticles", 2000))
        use_openai = bool(input_data.get("useOpenAI", False))
        priority_domain = input_data.get("priorityDomain", "top")
        enable_paid_tier = bool(input_data.get("enablePaidTier", False))

        # --- API Usage State Management ---
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        api_state = await Actor.get_value(API_STATE_KEY) or {
            "requests_today": 0,
            "last_reset_date": "1970-01-01"
        }

        if api_state.get("last_reset_date") != today_str:
            Actor.log.info(f"New day detected. Resetting API request counter from {api_state.get('requests_today')} to 0.")
            api_state = {"requests_today": 0, "last_reset_date": today_str}
        
        requests_today = api_state.get("requests_today", 0)
        Actor.log.info(f"API requests made today: {requests_today}/{FREE_TIER_DAILY_LIMIT}")

        # --- Deduplication setup ---
        processed_links_store = await Actor.open_key_value_store(name=PROCESSED_LINKS_STORE_NAME)

        # --- Prepare query ---
        query = quote_plus(keywords.replace(",", " OR ").strip())

        articles_fetched = 0
        max_pages = 200  # Safety limit for requests in a single run
        next_page = None

        async with aiohttp.ClientSession() as session:
            for page in range(1, max_pages + 1):
                if articles_fetched >= max_articles:
                    Actor.log.info(f"Target of {max_articles} articles reached. Stopping.")
                    break

                # --- Check API daily limit ---
                if not enable_paid_tier and requests_today >= FREE_TIER_DAILY_LIMIT:
                    Actor.log.warning(f"Free daily API request limit of {FREE_TIER_DAILY_LIMIT} reached. "
                                      "Enable the paid tier option to continue.")
                    break

                # --- Build NewsData API URL ---
                url = (
                    f"https://newsdata.io/api/1/news?"
                    f"apikey={NEWSDATA_API_KEY}&q={query}&category={category}"
                    f"&country={country}&language={language}&prioritydomain={priority_domain}"
                )
                if next_page:
                    url += f"&page={next_page}"

                Actor.log.info(f"Fetching page {page} -> {url}")

                data, success = await fetch_json(session, url)

                # --- Increment and save API request count on success ---
                if success:
                    requests_today += 1
                    api_state["requests_today"] = requests_today
                    await Actor.set_value(API_STATE_KEY, api_state)
                    Actor.log.info(f"API request successful. Today's count: {requests_today}/{FREE_TIER_DAILY_LIMIT}")

                if not data:
                    Actor.log.warning(f"No data returned for page {page}.")
                    break

                new_articles = data.get("results", [])
                if not isinstance(new_articles, list) or not new_articles:
                    Actor.log.info(f"No valid articles on page {page}. Stopping.")
                    break

                # --- Process and store each article ---
                for article in new_articles:
                    if articles_fetched >= max_articles:
                        break
                    
                    link = article.get("link")
                    if not link:
                        continue

                    # --- Deduplication Check using a safe key ---
                    safe_key = _get_safe_key(link)
                    if await processed_links_store.get_value(key=safe_key):
                        Actor.log.info(f"Skipping duplicate article: {link}")
                        continue

                    title = article.get("title", "Untitled")
                    description = article.get("description", "")
                    
                    summary = None
                    if use_openai and description:
                        summary = await summarize_with_openai(title, description)

                    await Actor.push_data({
                        "title": title,
                        "link": link,
                        "description": description,
                        "summary": summary,
                        "source": "newsdata.io",
                        "page": page,
                    })
                    articles_fetched += 1

                    # Mark link as processed to prevent future duplicates
                    await processed_links_store.set_value(key=safe_key, value=True)

                # --- Pagination handling ---
                next_page = data.get("nextPage")
                if not next_page:
                    Actor.log.info("No nextPage token found — reached end of results.")
                    break

        Actor.log.info(f"🎉 Finished. Fetched {articles_fetched} new articles in this run.")

if __name__ == "__main__":
    asyncio.run(main())