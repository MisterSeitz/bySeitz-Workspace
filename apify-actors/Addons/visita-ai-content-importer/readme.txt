=== Visita AI Content Importer ===
Contributors: visita
Tags: apify, ai, importer, automation, content generator
Requires at least: 6.0
Tested up to: 6.8
Requires PHP: 7.4
Stable tag: 1.0
License: GPLv2 or later
License URI: http://www.gnu.org/licenses/gpl-2.0.html

Connects WordPress to Apify to import AI posts, products, and listings automatically. Firewall-proof "Pull Method" for secure automation.

== Description ==

The Visita AI Content Importer allows you to automate your content publishing workflow by connecting your WordPress site directly to Apify.

Unlike standard push-based automations that often get blocked by firewalls (403/407 errors), this plugin uses a secure **"Pull Method"**. Your WordPress site wakes up on a schedule, securely fetches prepared content from your Apify Dataset, and imports it automatically.

**Key Features:**
* **Universal Compatibility:** Works with Posts, Pages, WooCommerce Products, MyListing types, and JetEngine Custom Post Types.
* **Firewall Proof:** Bypasses strict security (Cloudflare, LiteSpeed, QUIC.cloud) by initiating requests from the server side.
* **Media Sideloading:** Automatically downloads remote image URLs to your Media Library and sets them as Featured Images.
* **Gallery Support:** Creates native WordPress galleries or MyListing/JetEngine gallery fields from a list of URLs.
* **Taxonomy Mapping:** Automatically assigns Categories, Tags, or custom taxonomies (e.g., Regions, Brands).
* **Custom Fields:** Maps JSON meta data to WordPress Custom Fields (compatible with ACF).
* **Auto-Pilot:** Built-in hourly scheduler to fetch new content without manual intervention.

**How it Works:**
1.  You run an Apify Actor (e.g., connecting to OpenAI/ChatGPT) to generate content.
2.  The Actor saves the content to a standard Apify Dataset.
3.  This plugin checks that Dataset every hour.
4.  If new content is found, it is imported as a Draft or Published post immediately.

== External Services ==

This plugin relies on the Apify platform to retrieve content.
* **Service:** Apify (https://apify.com)
* **Terms of Use:** https://apify.com/terms
* **Privacy Policy:** https://apify.com/privacy-policy
* **Data Sent:** The plugin sends your private Apify API Token to the Apify API via a secure HTTPS request to authenticate access to your datasets. No other user data is shared.

== Installation ==

1.  Upload the plugin files to the `/wp-content/plugins/visita-ai-importer` directory, or install the plugin through the WordPress plugins screen directly.
2.  Activate the plugin through the 'Plugins' screen in WordPress.
3.  Go to **Settings > Visita AI Importer**.
4.  Enter your **Apify API Token**.
5.  (Optional) Enable "Automatic Sync" to fetch content hourly.

== Frequently Asked Questions ==

= Do I need an Apify account? =
Yes. You need an Apify account to generate the API Token required for this plugin to function.

= What Post Types does this support? =
It supports all registered Post Types. In the Apify input schema, you can specify `post`, `page`, `product` (WooCommerce), `job_listing` (MyListing), or any custom key like `services` (JetEngine).

= Does it work with Advanced Custom Fields (ACF)? =
Yes. Any data passed in the `meta` JSON object from Apify will be saved as post meta. If the key matches your ACF Field Name, the data will populate automatically.

== Upgrade Notice ==

= 1.0 =
Initial release.

== Screenshots ==

1. The Settings page where you enter your API Token and enable Auto-Sync.
2. The Manual Sync confirmation showing successfully imported posts.