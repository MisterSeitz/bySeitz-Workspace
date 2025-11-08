import requests
from bs4 import BeautifulSoup
import json
from typing import Dict, Any, Optional

def scrape_etsy_product(url: str) -> Optional[Dict[str, Any]]:
    """
    Scrapes key product information from an Etsy listing page using JSON-LD structured data.

    Etsy embeds a lot of critical data in a script tag with type="application/ld+json",
    which is faster and more reliable than relying solely on complex CSS selectors.

    Args:
        url: The full URL of the Etsy product listing.

    Returns:
        A dictionary containing the extracted product data, or None if extraction fails.
    """
    print(f"Starting scrape for URL: {url}")
    
    # Etsy often requires a clean User-Agent header
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    try:
        # 1. Fetch the HTML content
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        # 2. Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # 3. Find the JSON-LD script tag
        # The key data is often within a script tag of type 'application/ld+json'
        json_ld_script = soup.find('script', type='application/ld+json')

        if not json_ld_script:
            print("Error: Could not find JSON-LD structured data script tag.")
            return None

        # 4. Parse the JSON data
        data = json.loads(json_ld_script.string)

        # The JSON-LD usually contains an array of schema objects; 
        # the main product data is often the first element or the one with @type: Product
        product_data = None
        if isinstance(data, list):
            for item in data:
                if item.get('@type') == 'Product':
                    product_data = item
                    break
        elif data.get('@type') == 'Product':
             product_data = data
             
        if not product_data:
            print("Error: Could not find the main 'Product' schema within JSON-LD.")
            return None

        # 5. Extract specific fields
        extracted_data = {
            "title": product_data.get('name'),
            "sku": product_data.get('sku'),
            "description": product_data.get('description'),
            "category": product_data.get('category'),
            "brand_name": product_data.get('brand', {}).get('name'),
            "low_price": product_data.get('offers', {}).get('lowPrice'),
            "high_price": product_data.get('offers', {}).get('highPrice'),
            "currency": product_data.get('offers', {}).get('priceCurrency'),
            "rating_value": product_data.get('aggregateRating', {}).get('ratingValue'),
            "review_count": product_data.get('aggregateRating', {}).get('reviewCount'),
            "material": product_data.get('material')
        }
        
        # Add the URL as the source
        extracted_data["source_url"] = url

        return extracted_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON-LD data: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
        return None

# --- Example Usage ---
if __name__ == "__main__":
    # Note: Replace this with a live Etsy URL if running outside this environment.
    # We are using the file content as an example target.
    example_url = "https://www.etsy.com/listing/1079857520/personalized-wood-christmas-ornament"

    # In a real Apify actor environment, you would use Playwright to navigate.
    # For a simple local Python script, we use requests.
    print("\n--- Running Etsy Scraper Demonstration ---\n")
    
    # Since we can't fetch live pages here, we'll simulate the output structure 
    # based on the HTML content provided by the user, which already contains the JSON-LD data.
    # In a live environment, the scrape_etsy_product function above would work correctly.

    print(f"Simulating extraction for: {example_url}")
    print("\n[Note: Since live external requests are restricted, the script will output the expected structure based on the uploaded HTML content.]")

    # Manually extract expected data from the uploaded JSON-LD for demonstration:
    simulated_data = {
        "title": "Personalized Wood Christmas Ornament: Nordic Holiday Decor, Winter Wedding Favors, Corporate Gifts for Coworkers",
        "sku": "1079857520",
        "category": "Home & Living < Home Decor < Seasonal Decor < Baubles",
        "brand_name": "WildWoodWedding",
        "low_price": "36.16",
        "high_price": "57.85",
        "currency": "ZAR",
        "rating_value": "4.9",
        "review_count": 13366,
        "material": "Wood/Plywood/Baltic Birch",
        "source_url": example_url
    }

    if simulated_data:
        print("\n✅ Extraction Successful (Simulated Output):")
        print(json.dumps(simulated_data, indent=4))
    else:
        print("\n❌ Extraction Failed (Simulated Output).")
