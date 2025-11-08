# YouTube Transcript, Comment, and Metadata Scraper

This actor scrapes YouTube videos for full transcripts (captions), the first page of comments, and key metadata (title, channel, views, and likes). It can discover videos based on search queries or scrape a specific list of video IDs.

This actor uses a robust hybrid approach:
* **Playwright** is used to load the page, handle popups, scroll, and scrape metadata and comments.
* **`youtube-caption-extractor` library** is used to reliably fetch transcripts directly, avoiding common browser-based scraping failures.

## Features

* Scrapes full video transcripts (captions) in your chosen language.
* Scrapes the first page of comments (approx. 20 comments).
* Scrapes metadata: title, channel, view count, and like count.
* **Discover Mode:** Finds videos to scrape based on search queries.
* **Scrape Mode:** Scrapes a specific, user-provided list of video IDs.

## Input Configuration

The actor's behavior is controlled by the input, which has the following fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `runMode` | String | **Required.** Choose the actor's operating mode.<br>• **`discover`**: Find new videos using search.<br>• **`scrape`**: Scrape specific videos from `videoIDs`. |
| `discoverConfig` | Object | Configuration for **Discover Mode**. |
| `scrapeConfig` | Object | Configuration for **Scrape Mode**. |
| `lang` | String | The language code for the transcript you want (e.g., `en`, `es`, `fr`). Defaults to `en`. |

### `discoverConfig` Settings

| Field | Type | Description |
| :--- | :--- | :--- |
| `searchQueries` | Array | **Required.** A list of search terms to find videos. The actor will use the first one. |
| `searchCategory` | String | *Optional.* A category keyword (e.g., "Sport", "News") to append to the search. |
| `uploadDate` | String | *Optional. This filter is not yet implemented in the code.* |
| `videoDuration` | String | *Optional. This filter is not yet implemented in the code.* |
| `maxResultsPerQuery` | Integer | The maximum number of videos to find for the search query. Defaults to `5`. |

### `scrapeConfig` Settings

| Field | Type | Description |
| :--- | :--- | :--- |
| `videoIDs` | Array | **Required.** A list of YouTube video IDs (e.g., `xZCbAki4puY`) to scrape. |

## Output Structure

The actor saves its results to the dataset, which will be displayed in the **Output** tab. Each item represents one scraped video.

| Field | Type | Description |
| :--- | :--- | :--- |
| `videoId` | String | The unique ID of the scraped video. |
| `title` | String | The full title of the video. |
| `channel` | String | The name of the YouTube channel. |
| `views` | String | The view count (e.g., "1.2M views"). |
| `likes` | String | The like count (e.g., "10K likes"). |
| `transcriptMerged` | String | The full, merged transcript as a single block of text. |
| `comments` | String | A JSON string containing an array of comment objects. Each object has `{ author, text, likes }`. |
| `_chargeStatus` | String | A status message showing what you were charged for (e.g., "Metadata: Charged, Captions: Charged..."). |
| `error` | String | If an error occurred for this video, it will be noted here. |

## Limitations

* **Comments:** The actor currently scrapes only the first page of comments (approx. 20). It does not perform infinite scrolling to load all comments.
* **Discover Filters:** The `uploadDate` and `videoDuration` filters in "Discover Mode" are not yet implemented. The actor will find the top results regardless of these settings.

## 💰 Pricing (Pay-Per-Event)

This actor uses a **Pay-Per-Event (PPE)** pricing model. You pay a tiny fee to start the actor, and then a separate, small fee for each piece of data you *successfully* retrieve for each video.

This gives you granular control over your costs. If you only scrape metadata, you only pay for metadata.

| Event Name | Title | Description |
| :--- | :--- | :--- |
| **`apify-actor-start`** | Actor Start Fee | This is the recommended base fee for *initiating* the actor run. |
| **`metadata-retrieved`** | Metadata Retrieved | Charged **per video** for successfully scraping its metadata (title, channel, views, etc.). |
| **`captions-retrieved`** | Captions Retrieved | Charged **per video** *only if* a transcript is successfully found and extracted. |
| **`comments-retrieved`** | Comments Retrieved | Charged **per video** *only if* comments are successfully found and scraped. |

You can set your own prices for these events in the **Publication** tab of the actor's settings.