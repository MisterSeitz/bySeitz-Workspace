## What is Yellow Pages Scraper?

The **Yellow Pages Scraper** is a fast and reliable tool for extracting public business data from **[YP.com](https://www.yellowpages.com/)**. Simply provide a search term (like "plumbers" or "restaurants") and a location (like "New York, NY" or "90210"), and the Actor will scrape and structure the business listings for you.

This Actor is built to be a simple, fast, and reliable replacement for a direct **Yellow Pages API**. It does not use any AI, relying instead on direct website selectors for maximum speed and data consistency.

## What can this Yellow Pages Scraper do?

  * **Scrape Key Business Details:** Extracts essential data points like **business name**, **phone number**, **full address**, and **website**.
  * **Get Rich Information:** Gathers operational details, including **business hours**, accepted **payment methods**, "Years in Business," listed **neighborhoods**, and **social media links**.
  * **Find Categories & Reviews:** Scrapes all listed business categories and captures the average **star rating** and total **review count**.
  * **Collect All Data:** Can extract **gallery image URLs**, business **logos**, "Also Known As" (AKA) names, and the "General Info" description.
  * **Run on the Apify Platform:** Benefit from the full power of the Apify cloud. You can run scrapes on a **schedule**, use smart **proxy rotation** to avoid blocks, and integrate with any other app or workflow using Apify's [API](https://docs.apify.com/api/v2).
  * **Download Your Data Easily:** Get your data in structured formats like **JSON, CSV, and Excel** as soon as the scrape is finished.

## What data can Yellow Pages Scraper extract?

The scraper extracts the following data points for each business listing:

| Field | Description |
| :--- | :--- |
| `crawl_url` | The YP.com URL of the business listing. |
| `business_name` | The name of the business. |
| `phone_number` | The primary phone number. |
| `full_address` | The complete street address, city, state, and ZIP. |
| `website_url` | The business's website. |
| `rating` | The average star rating (e.g., "5"). |
| `review_count` | The total number of reviews (e.g., "1"). |
| `categories` | A list of all business categories. |
| `business_hours` | Formatted hours (e.g., "Mon - Fri: 9:00 am - 5:00 pm"). |
| `email` | The business email (if public). |
| `claimed_status` | "Claimed" or "Unclaimed". |
| `payment_methods`| List of accepted payment methods. |
| `social_links` | List of links to social media profiles. |
| `general_info` | The "General Info" description. |

-----

## How do I use Yellow Pages Scraper?

1.  Go to the Actor's task in the [Apify Console](https://console.apify.com/).
2.  Enter your **Search Terms** (e.g., `Architects`, `Plumbers`).
3.  Enter the **Locations** (e.g., `New York, NY`, `11746`).
4.  Set the **Total Businesses to Scrape** (e.g., `50`).
5.  Click **Start** and wait for the run to finish.
6.  Go to the **Storage** tab to download your data in JSON, CSV, or Excel.

---

## How much will it cost to scrape Yellow Pages?

This scraper is monetized using the **Pay Per Event (PPE)** model. You are charged a small fee for the Actor start and for each business profile that is successfully scraped.

Based on your current settings, the pricing is as follows:

| Event | Price | Description |
| :--- | :--- | :--- |
| **Actor Start** (`apify-actor-start`) | $0.00005 | Charged automatically at the start of each Actor run to cover startup costs. |
| **Scraped Business Item** (`scraped-business-item`) | $0.007 | Charged for each business profile successfully scraped and saved to the dataset. |

**Discounts for `scraped-business-item`:**
* **Bronze plan:** $0.00633
* **Silver plan:** $0.00567
* **Gold plan:** $0.005

The Actor is designed to respect the **Max cost per run** limit set in your input. It scrapes one business at a time and will stop automatically if the cost limit is reached.

---

## Input and Output Examples

### Input Example

The input is simple. You only need to provide search terms, locations, and the number of businesses you want.

```json
{
  "searchQueries": [
    "Architects",
    "Interior Design"
  ],
  "locations": [
    "New York, NY"
  ],
  "maxTotalBusinesses": 5
}
```

### Output Example

The Actor will return a dataset of structured business data.

```json
[{
  "crawl_url": "https://www.yellowpages.com/new-york-ny/mip/jbj-concept-523768808",
  "business_name": "JBJ Concept",
  "phone_number": "(646) 221-9138",
  "full_address": "313 E 61st St, New York, NY 10065",
  "website_url": "http://www.jbjconcept.com",
  "rating": null,
  "review_count": null,
  "categories": [
    "Architects & Builders Services",
    "Architectural Designers",
    "Home Improvements",
    "Home Repair & Maintenance"
  ],
  "general_info": "A multitalented interior designer, experienced with creating dynamic and eye catching design from concept through execution...",
  "logo_url": "https://i3.ypcdn.com/blob/29c88eaeb99ecd0a936b83fd5cb5effe07edbc48",
  "services_products": "Interior Design for Commercial & Residential JBJ CONCEPT is a New York based...",
  "payment_methods": ["discover", "master card", "visa", "amex", "check", "debit"],
  "aka": ["Jbj Concept"],
  "neighborhoods": ["Upper East Side", "Upper Manhattan"],
  "other_links": ["http://www.jbjconcept.com"],
  "social_links": [],
  "email": "joseph.by@hotmail.com",
  "business_hours": "Mon - Thu: 10:00 am - 8:00 pm | Fri: 10:00 am - 3:00 pm | Sat: Closed | Sun: 9:00 am - 9:00 pm",
  "claimed_status": "Claimed",
  "gallery_image_urls": ["https://i1.ypcdn.com/blob/070376..._228x168_crop.jpg"],
  "years_in_business": "22 Years in Business",
  "places_near_with_category": ["Brooklyn: /brooklyn-ny/architects-builders-services", "..."],
  "crawl_error": null
}]
```

-----

## Troubleshooting & Support

  * **USA Only:** Yellow Pages (YP.com) is a US-based directory. You **must** use a **US Residential Proxy** for this Actor to work. The input configuration is set to this by default.
  * **Report Issues:** If you find a bug, a field is not being scraped correctly, or the site structure has changed, please open an issue in the **Issues** tab.

## Is it legal to scrape Yellow Pages?

Our scrapers are ethical and do not extract any private user data, such as email addresses, gender, or location. They only extract what the user has chosen to share publicly. We therefore believe that our scrapers, when used for ethical purposes by Apify users, are safe. However, you should be aware that your results could contain personal data. Personal data is protected by the GDPR in the European Union and by other regulations around the world. You should not scrape personal data unless you have a legitimate reason to do so. If you're unsure whether your reason is legitimate, consult your lawyers. You can also read our blog post on the [legality of web scraping](https://blog.apify.com/is-web-scraping-legal/).