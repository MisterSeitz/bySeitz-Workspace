# scraper_logic.py - Core Yellow Pages Scraper Logic (Selector-Based, PPE Enabled)

import json
import asyncio
import os
import re 
from typing import List, Dict, Any, Type, Optional
from datetime import datetime

from bs4 import BeautifulSoup
# Pydantic import removed - it is no longer used.

# --- CORE EXTERNAL DEPENDENCIES ---
import httpx 
from playwright.async_api import async_playwright
import random

# --- NEW APIFY SDK IMPORT ---
from apify import Actor

# --- 1. Custom Fetching Utilities ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

LINK_CACHE_KEY = "PROCESSED-BUSINESS-LINKS" 

def _load_processed_links() -> List[str]:
    try:
        apify_kv_path = os.environ.get("APIFY_STORAGE_PATH")
        if apify_kv_path:
            filepath = os.path.join(apify_kv_path, 'key_value_stores', 'default', f'{LINK_CACHE_KEY}.json')
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        return []
    except Exception as e:
        print(f"⚠️ Warning: Could not load processed links from cache. Starting fresh. Error: {e}")
        return []

def _save_processed_links(links: List[str]):
    try:
        apify_kv_path = os.environ.get("APIFY_STORAGE_PATH")
        if apify_kv_path:
            kv_dir = os.path.join(apify_kv_path, 'key_value_stores', 'default')
            os.makedirs(kv_dir, exist_ok=True)
            filepath = os.path.join(kv_dir, f'{LINK_CACHE_KEY}.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(links, f, indent=2)
    except Exception as e:
        print(f"⚠️ Warning: Could not save processed links to cache. Error: {e}")

def generate_yp_search_urls(queries: List[str], locations: List[str]) -> List[str]:
    """Generates Yellow Pages search URLs for all combinations of queries and locations."""
    urls = []
    base_url = "https://www.yellowpages.com/search?"
    for query in queries:
        for location in locations:
            params = {'search_terms': query.replace(' ', '+'), 'geo_location_terms': location.replace(' ', '+')}
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            urls.append(base_url + query_string)
    return urls

async def fetch_business_links(queries: List[str], locations: List[str], max_per_page: int, max_total: int, processed_links: List[str], proxy_config_instance: Optional[Any], verbose: bool = False) -> List[str]:
    """
    Scrapes Business Detail Page (PDP) URLs from a list of Yellow Pages search result pages.
    """
    search_urls = generate_yp_search_urls(queries, locations)
    all_pdp_links = []
    processed_set = set(processed_links)
    
    print(f"🔎 -> Gathering links from {len(search_urls)} YP search URLs. Skipping {len(processed_set)} previously processed links...")
    
    try:
        async with async_playwright() as p:
            user_agent = random.choice(USER_AGENTS)
            
            proxy_config = {}
            if proxy_config_instance:
                 try:
                     proxy_url = await proxy_config_instance.new_url()
                     proxy_config = {"server": proxy_url}
                     if verbose: print(f"  -> 🛡️ Using proxy for search results: {proxy_url.split('@')[-1]}")
                 except Exception as e:
                     if verbose: print(f"  -> ⚠️ Warning: Failed to get proxy for search page: {e}")

            browser = await p.chromium.launch(
                headless=True,
                proxy=proxy_config if proxy_config else None,
            )
            context = await browser.new_context(
                user_agent=user_agent,
                ignore_https_errors=True,
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()

            for search_url in search_urls:
                if len(all_pdp_links) >= max_total:
                    break
                
                print(f"  -> 📄 Processing search URL: {search_url}")

                SEARCH_PAGE_TIMEOUT_MS = 120000 
                await page.goto(search_url, wait_until="load", timeout=SEARCH_PAGE_TIMEOUT_MS) 

                search_results_selector = 'div.organic div.result'
                try:
                    await page.wait_for_selector(search_results_selector, state="visible", timeout=60000) 
                    if verbose: print("  -> ✅ Search results container found.")
                except Exception as e:
                    if verbose: print(f"  -> ❌ Could not find search results container. Page might be empty or blocked. Skipping.")
                    content = await page.content()
                    if "captcha" in content.lower() or "robot check" in content.lower():
                        print("  -> 🤖 CRITICAL: CAPTCHA detected on search page. Skipping search query.")
                    continue 

                product_link_elements = await page.locator(f'{search_results_selector} a.business-name').all()
                
                links_found = 0
                for element in product_link_elements:
                    href = await element.get_attribute('href')
                    if href and not href.startswith(('http', 'javascript:')):
                        base_url = "https://www.yellowpages.com"
                        full_url = base_url + href
                        clean_url = full_url.split('?')[0].split('/ref=')[0] 
                        
                        if clean_url not in processed_set:
                            all_pdp_links.append(clean_url)
                            processed_set.add(clean_url)
                            links_found += 1
                        
                        if len(all_pdp_links) >= max_total:
                            break
                
            await browser.close()
            
    except Exception as e:
        print(f"💥 CRITICAL: Failed to scrape search results (Anti-bot block likely): {e}")
        return []
        
    return all_pdp_links


# --- 2. Core Scraper Class (Simplified) ---
class YellowPagesScraper:
    """
    Selector-based scraper class for Yellow Pages, configured for PPE.
    """

    def __init__(self, input_data: Dict[str, Any]):
        self.config = input_data
        self.search_queries = self.config["searchQueries"]
        self.locations = self.config["locations"]
        self.max_per_page = self.config["maxBusinessesPerSearchPage"]
        self.max_total = self.config["maxTotalBusinesses"]
        self.verbose = self.config.get("verboseLog", False)
        
        self.http_client = httpx.AsyncClient(
            headers={'User-Agent': random.choice(USER_AGENTS)},
            follow_redirects=True,
            timeout=30.0
        )
            
    async def _fetch_and_parse_html(self, url: str) -> Optional[str]:
        """
        Fetches the full HTML content of a page using Playwright.
        """
        PAGE_TIMEOUT_MS = 120000 
        RANDOM_WAIT = random.uniform(2, 5)

        if self.verbose: print(f"  -> 🌐 Scraping: {url}")
        browser = None
        try:
            proxy_url = None
            proxy_config = {}
            if self.config.get("proxy_config_instance"):
                 session_id = re.sub(r'[^a-zA-Z0-9_-]', '_', url.split('.com/')[-1])
                 
                 proxy_url = await self.config["proxy_config_instance"].new_url(session_id=session_id)
                 proxy_config = {"server": proxy_url}
                 if self.verbose: print(f"  -> 🛡️ Using proxy with session ID: {session_id}")

            async with async_playwright() as p:
                user_agent = random.choice(USER_AGENTS)
                
                browser = await p.chromium.launch(
                    headless=True,
                    proxy=proxy_config if proxy_config else None,
                )
                
                context = await browser.new_context(
                    user_agent=user_agent,
                    ignore_https_errors=True,
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                await page.goto(url, wait_until="load", timeout=PAGE_TIMEOUT_MS) 
                
                try:
                    # Gate 1: Wait for the title
                    await page.wait_for_selector('h1.business-name', timeout=PAGE_TIMEOUT_MS)
                    if self.verbose: print(f"  -> ✅ h1.business-name found. Waiting {RANDOM_WAIT:.2f}s...")
                    await asyncio.sleep(RANDOM_WAIT)
                    
                    # Gate 2: Wait for the dynamic phone number
                    if self.verbose: print("  -> ⏳ Waiting for dynamic content (a.phone.dockable)...")
                    await page.wait_for_selector('a.phone.dockable', state="visible", timeout=30000)
                    if self.verbose: print("  -> ✅ Dynamic content (a.phone.dockable) found.")
                    
                except Exception as e:
                    content = await page.content()
                    if "captcha" in content.lower() or "robot check" in content.lower():
                         raise Exception("Scraping blocked: Detected CAPTCHA page.")
                    if "a.phone.dockable" in str(e):
                         raise Exception("Scraping failed: Page loaded but dynamic content (a.phone.dockable) never appeared.")
                    raise e
                
                html_content = await page.content()
                
                if len(html_content.strip()) < 500: # Check for minimal HTML
                     raise Exception("Minimal content extracted (less than 500 bytes).")

                return html_content
            
        except Exception as e:
            if self.verbose: 
                 if "Timeout" in str(e):
                      print(f"  -> ❌ Error fetching or processing {url}, exception: TimeoutError: The page took longer than {PAGE_TIMEOUT_MS/1000}s to load.")
                 else:
                      print(f"  -> ❌ Error fetching or processing {url}, exception: {type(e).__name__}: {e}")
            return None 
        finally:
            if browser:
                await browser.close()
    
    # --- Helper functions for selector-based scraping ---
    def _get_text(self, soup: BeautifulSoup, selector: str, default: Optional[str] = None) -> Optional[str]:
        element = soup.select_one(selector)
        return ' '.join(element.text.split()) if element else default # Cleans whitespace

    def _get_href(self, soup: BeautifulSoup, selector: str, default: Optional[str] = None) -> Optional[str]:
        element = soup.select_one(selector)
        return element['href'] if element and element.has_attr('href') else default

    def _get_all_text(self, soup: BeautifulSoup, selector: str) -> List[str]:
        return [ ' '.join(el.text.split()) for el in soup.select(selector)]

    def _get_all_hrefs(self, soup: BeautifulSoup, selector: str) -> List[str]:
        return [el['href'] for el in soup.select(selector) if el.has_attr('href')]

    def _get_dt_dd_content(self, soup: BeautifulSoup, dt_text: str) -> Optional[str]:
        # Find all dt elements
        dt_elements = soup.find_all('dt')
        for dt_element in dt_elements:
            if dt_text.lower() in (dt_element.text or "").lower():
                dd_element = dt_element.find_next_sibling('dd')
                if dd_element:
                    # Clean up excessive newlines and spacing
                    return ' '.join(dd_element.text.split())
        return None
    
    async def _run_selector_path(self, url: str) -> Optional[Dict]:
        """
        Tier 1 Logic: Executes Fetch -> Parse HTML and outputs structured data using selectors.
        """
        html_content = await self._fetch_and_parse_html(url)
        if not html_content:
            return {
                "crawl_url": url,
                "crawl_error": "Content Extraction Failed (Playwright failed or extracted minimal content)."
            }

        soup = BeautifulSoup(html_content, 'lxml') # Use lxml for speed
        data = {"crawl_url": url} # --- FIX: Renamed 'url' to 'crawl_url' ---
        
        try:
            # Main Info
            data['business_name'] = self._get_text(soup, 'h1.business-name')
            data['phone_number'] = self._get_text(soup, 'a.phone.dockable span.full') or self._get_text(soup, 'a.phone.dockable')
            
            # --- FIX for Full Address ---
            data['full_address'] = self._get_text(soup, 'a.directions .address')
            
            data['website_url'] = self._get_href(soup, 'a.website-link.dockable')
            data['claimed_status'] = "Claimed" if soup.select_one('div#claimed') else "Unclaimed"
            
            # Rating
            rating_element = soup.select_one('section.ratings .rating-stars')
            if rating_element:
                rating_classes = rating_element.get('class', [])
                rating_map = {'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5'}
                for r_class in rating_classes:
                    if r_class in rating_map:
                        data['rating'] = rating_map[r_class]
                        if 'half' in rating_classes:
                            data['rating'] = f"{data['rating']}.5"
                        break
            
            review_count_text = self._get_text(soup, 'section.ratings .count')
            if review_count_text:
                data['review_count'] = review_count_text.strip('()')

            # Categories (deduplicated)
            data['categories'] = list(dict.fromkeys(self._get_all_text(soup, 'div.categories a, dd.categories a')))
            
            # --- FIX for Business Hours ---
            hours_list = []
            hours_table = soup.select('div.open-details table tr')
            if hours_table:
                for row in hours_table:
                    day = self._get_text(row, 'th.day-label')
                    time = self._get_text(row, 'td.day-hours')
                    if day and time:
                        hours_list.append(f"{day.strip(':')} {time}")
                data['business_hours'] = " | ".join(hours_list) if hours_list else None
            else:
                # Fallback for pages without a table (e.g., "Add Hours")
                hours_text = self._get_text(soup, 'div.open-details')
                data['business_hours'] = hours_text.replace("Regular Hours", "").strip() if hours_text and "Add Hours" not in hours_text else None

            # --- FIX for Years in Business ---
            years_text = self._get_text(soup, 'div.years-in-business .count strong')
            if years_text:
                data['years_in_business'] = f"{years_text} Years in Business"
            else:
                years_text = self._get_text(soup, 'div.years-with-yp .count strong')
                data['years_in_business'] = f"{years_text} Years with Yellow Pages" if years_text else None

            # Gallery
            data['gallery_image_urls'] = [img['src'] for img in soup.select('a.media-thumbnail.collage-pic img') if img.has_attr('src')]
            
            # "More Info" Section
            more_info_section = soup.select_one('section#business-info')
            if more_info_section:
                data['general_info'] = self._get_text(more_info_section, 'dd.general-info')
                
                # --- FIX for Email ---
                email_href = self._get_href(more_info_section, 'a.email-business')
                data['email'] = email_href.replace('mailto:', '').strip() if email_href else None
                
                payment_text = self._get_dt_dd_content(more_info_section, 'Payment method')
                data['payment_methods'] = [p.strip() for p in payment_text.split(',')] if payment_text else []
                
                # --- FIX for AKA ---
                data['aka'] = self._get_all_text(more_info_section, 'dd.aka p')

                data['neighborhoods'] = self._get_all_text(more_info_section, 'dd.neighborhoods a')
                data['other_links'] = self._get_all_hrefs(more_info_section, 'dd.weblinks a.other-links')
                data['services_products'] = self._get_dt_dd_content(more_info_section, 'Services/Products')
                data['logo_url'] = soup.select_one('dd.logo img')['src'] if soup.select_one('dd.logo img') else None
                
                # --- NEW: Social Links ---
                data['social_links'] = self._get_all_hrefs(more_info_section, 'dd.social-links a')

            # Places Near
            places_near_links = soup.select('section.cross-links ul li a')
            data['places_near_with_category'] = [f"{a.text.strip()}: {a['href']}" for a in places_near_links if a.has_attr('href')]

            return data
        
        except Exception as e:
            if self.verbose: print(f"  -> ❌ Selector-based scrape failed for {url}: {e}")
            return {
                "crawl_url": url,
                "crawl_error": f"Selector extraction failed: {e}" # --- FIX: Renamed 'ai_error'
            }
                
    async def run(self) -> None:
        """
        Runs the entire pipeline, processing items sequentially to respect PPE limits.
        """
        print(f"--- 🏃‍♂️ Running TIER 1: CRAWL ONLY MODE (Selector-based, PPE Enabled) ---") 
        
        processed_links = _load_processed_links()
        
        # STEP 1. Source Gathering
        try:
            source_links = await fetch_business_links(
                self.search_queries, 
                self.locations,
                self.max_per_page, 
                self.max_total, 
                processed_links,
                self.config.get("proxy_config_instance"),
                self.verbose
            ) 
        except Exception as e:
            print(f"💥 CRITICAL FAILURE during link gathering: {e}")
            # Push a single error item
            await Actor.push_data([{"crawl_url": "CRITICAL_FAILURE", "business_name": "Scraper failed during link gathering.", "crawl_error": f"Critical Failure during link gathering. Error: {e}"}])
            await self.http_client.aclose()
            return
            
        if not source_links:
             print("ℹ️ -> No new businesses found to process.")
             await Actor.push_data([{"crawl_url": "NO_NEW_BUSINESSES", "business_name": "No new businesses found."}])
             await self.http_client.aclose()
             return

        # STEP 2. Per-Item Processing and Charging
        print(f"⚙️ -> Processing {len(source_links)} businesses one by one to respect spending limits.")
        
        crawled_urls = []
        try:
            for link in source_links:
                data = await self._run_selector_path(link)
                crawled_urls.append(link) # Add to cache even if scrape fails
                
                if not data:
                    print(f"  -> ⚠️ Failed to scrape data for {link}, skipping push.")
                    # Push error data for this specific URL
                    await Actor.push_data({"crawl_url": link, "crawl_error": "Failed to fetch or parse HTML."})
                    continue

                # --- CHARGE PER ITEM ---
                # This event name 'scraped-business-item' must be defined
                # in your Actor's "Monetization" tab in Apify Console.
                #
                # *** THIS IS THE FIX: Use a positional argument, not a keyword argument. ***
                charge_result = await Actor.push_data(data, 'scraped-business-item')


                # --- RESPECT SPENDING LIMIT ---
                if charge_result and charge_result.event_charge_limit_reached:
                    print(f"  -> 🛑 User spending limit reached after scraping {link}. Stopping run.")
                    break
            
        except Exception as e:
            print(f"💥 CRITICAL EXECUTION FAILURE during processing loop: {e}")
            await Actor.push_data([{"crawl_url": "CRITICAL_FAILURE", "business_name": "Scraper failed during processing loop.", "crawl_error": f"Critical Failure during page processing. Error: {e}"}])
        
        finally:
            # STEP 3. Finalization
            await self.http_client.aclose() 
            _save_processed_links(list(set(processed_links + crawled_urls)))
            print(f"🏁 -> Processed {len(crawled_urls)} businesses. Run finished.")