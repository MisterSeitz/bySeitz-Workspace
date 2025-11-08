# src/__main__.py
# Make sure this is the file you are editing.

import asyncio
from apify import Actor
# This line is corrected to import the new class name
from .scraper_logic import YellowPagesScraper 

async def main():
    """
    Main Apify actor entrypoint.
    Initializes the Actor, gets input, sets up US-based proxy,
    and runs the YellowPagesScraper.
    """
    async with Actor:
        print("🏁 --- Yellow Pages Scraper Starting --- 🏁")
        
        input_data = await Actor.get_input()
        if not input_data:
            print("❌ ERROR: No input found. Exiting.")
            await Actor.fail()
            return

        # --- Proxy Configuration ---
        # YellowPages.com is US-only and requires a good proxy
        # We will force the proxy to use US Residential IPs.
        proxy_config_input = input_data.get('proxyConfiguration', {})
        proxy_config_input['proxyGroups'] = ['RESIDENTIAL'] 
        proxy_config_input['countryCode'] = 'US' 

        print(f"🇺🇸 -> Forcing US Residential Proxy for YellowPages.com access.")

        try:
            proxy_configuration = await Actor.create_proxy_configuration(
                actor_proxy_input=proxy_config_input
            )
            # Pass the usable proxy object to the scraper class
            input_data["proxy_config_instance"] = proxy_configuration
        except Exception as e:
            print(f"❌ ERROR: Failed to create proxy configuration. {e}")
            await Actor.fail()
            return
        
        # --- Run Scraper ---
        try:
            # This line is corrected to use the new class name
            scraper = YellowPagesScraper(input_data) 
            await scraper.run()
            print("✅ --- Yellow Pages Scraper Finished --- ✅")
        except Exception as e:
            print(f"💥 CRITICAL: Scraper run failed. Error: {e}")
            await Actor.fail()

if __name__ == "__main__":
    asyncio.run(main())