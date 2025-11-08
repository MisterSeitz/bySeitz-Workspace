import requests
from bs4 import BeautifulSoup
import re

# The URL of the specific DMRE media advisory post to scrape.
TARGET_URL = "https://www.dmre.gov.za/news-room/post/2875/media-advisory-minister-of-electricity-and-energy-to-unpack-irp-2025"

def scrape_dmre_article(url):
    """
    Fetches, parses, and extracts the title and body content from a DMRE news article.
    
    Args:
        url (str): The URL of the article to scrape.
    """
    print(f"Attempting to scrape URL: {url}\n")
    
    try:
        # 1. Fetch the page content
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        
        # Raise HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status() 

        # 2. Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # 3. Extract the Title and locate the main article content wrapper.
        # Based on the provided HTML, the main article is wrapped in 'dnnViewEntry'.
        article_wrapper = soup.find('div', class_='dnnViewEntry')

        title = "Title Not Found"
        if article_wrapper:
            # The title is specifically in an H2 tag within this wrapper.
            title_element = article_wrapper.find('h2')
            if title_element:
                title = title_element.text.strip()
        
        # 4. Extract the Body Content
        # The main body text is specifically located in a div with class 'vbBody'.
        content_container = article_wrapper.find('div', class_='vbBody') if article_wrapper else None
            
        body_text = []
        if content_container:
            # Extract all paragraph (<p>) and list item (<li>) tags within the container.
            paragraphs = content_container.find_all(['p', 'li'])
            
            for p in paragraphs:
                # Use get_text(strip=True) to clean up whitespace around text elements.
                text = p.get_text(strip=True)
                # Only include non-empty lines
                if text:
                    body_text.append(text)
        
        full_body = "\n\n".join(body_text) if body_text else "Article Body Not Found. Check CSS selectors."
        
        # 5. Output the results
        print("-" * 50)
        print(f"SCRAPE RESULTS FOR: {title}")
        print("-" * 50)
        print(f"\nTITLE:\n{title}")
        print(f"\nBODY CONTENT:\n{full_body}")
        print("-" * 50)

    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error occurred: {err} - Status Code: {response.status_code}")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred while fetching the URL: {err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    scrape_dmre_article(TARGET_URL)