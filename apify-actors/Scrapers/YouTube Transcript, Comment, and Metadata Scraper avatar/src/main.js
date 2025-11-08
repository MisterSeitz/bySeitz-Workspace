import { Actor, log } from 'apify';
import { chromium } from 'playwright';
import { scrapeTranscript } from './transcript_scraper.js';

await Actor.main(async () => {
    log.info('🚀 Actor started — YouTube Transcript Scraper initialized.');

    const input = await Actor.getInput();
    const {
        runMode = 'discover',
        discoverConfig = {},
        scrapeConfig = {},
        lang = 'en'
    } = input || {};

    const urlsToScrape = [];

    // --- 1. POPULATE URLS TO SCRAPE ---
    if (runMode === 'discover') {
        log.info('🔎 Discovering YouTube videos...');
        // ... (rest of discover logic is unchanged)
        const browser = await chromium.launch({ headless: true });
        const page = await browser.newPage();
        const searchQuery = discoverConfig.searchQueries?.[0] || 'latest news';
        const searchCategory = discoverConfig.searchCategory ? ` ${discoverConfig.searchCategory}` : '';
        const finalQuery = `${searchQuery}${searchCategory}`;
        const maxResults = discoverConfig.maxResultsPerQuery || 5;
        log.info(`🕵️ Searching for: ${finalQuery}`);
        await page.goto(`https://www.youtube.com/results?search_query=${encodeURIComponent(finalQuery)}`, {
            waitUntil: 'domcontentloaded'
        });
        await page.waitForSelector('ytd-video-renderer', { timeout: 20000 });
        const videoLinks = await page.$$eval(
            'ytd-video-renderer a[href*="/watch"]',
            (els) => els.map(a => new URL(a.href, 'https://www.youtube.com').href)
        );
        const uniqueVideos = [...new Set(videoLinks)]
            .filter(url => url.includes('watch?v='))
            .slice(0, maxResults);
        await browser.close();
        log.info(`✅ Found ${uniqueVideos.length} videos for "${finalQuery}"`);
        urlsToScrape.push(...uniqueVideos);

    } else if (runMode === 'scrape') {
        // ... (rest of scrape logic is unchanged)
        log.info('✍️ Scraping videos from provided IDs...');
        const videoIDs = scrapeConfig.videoIDs || [];
        if (videoIDs.length === 0) {
            log.warning('No Video IDs provided in "scrape" mode. Actor will exit.');
            await Actor.exit();
        }
        log.info(`Found ${videoIDs.length} video IDs to scrape.`);
        for (const id of videoIDs) {
            urlsToScrape.push(`https://www.youtube.com/watch?v=${id}`);
        }
    }

    // --- 2. RUN THE SCRAPER ---
    if (urlsToScrape.length === 0) {
        log.warning('No videos to scrape. Actor finishing.');
        await Actor.exit();
    }

    log.info(`▶️ Starting scrape for ${urlsToScrape.length} videos.`);

    for (const videoUrl of urlsToScrape) {
        const result = await scrapeTranscript(videoUrl, lang);

        if (result.error) {
            log.warning(`Failed to scrape ${videoUrl}: ${result.error}`);
            await Actor.pushData({
                videoId: videoUrl.split('v=')[1]?.split('&')[0] || null,
                title: result.metadata?.title || 'Unknown (scrape failed)',
                error: result.error,
            });
        } else {
            // --- NEW: CHARGE FOR EVENTS ---
            let metadataCharged = false;
            let captionsCharged = false;
            let commentsCharged = false;

            // --- ADDED METADATA CHARGE ---
            // This runs for every successfully processed video
            const metaChargeResult = await Actor.charge({ eventName: "metadata-retrieved" });
            if (metaChargeResult.eventChargeLimitReached) {
                log.warning('User spending limit reached for "metadata-retrieved". Stopping actor.');
                await Actor.exit();
                return; // Stop the loop
            }
            metadataCharged = true;
            // --- END METADATA CHARGE ---

            // Charge for captions if we found them
            if (result.transcriptMerged) {
                const chargeResult = await Actor.charge({ eventName: "captions-retrieved" });
                if (chargeResult.eventChargeLimitReached) {
                    log.warning('User spending limit reached for "captions-retrieved". Stopping actor.');
                    await Actor.exit();
                    return; // Stop the loop
                }
                captionsCharged = true;
            }

            // Charge for comments if we found them
            if (result.comments && result.comments.length > 0) {
                const chargeResult = await Actor.charge({ eventName: "comments-retrieved" });
                if (chargeResult.eventChargeLimitReached) {
                    log.warning('User spending limit reached for "comments-retrieved". Stopping actor.');
                    await Actor.exit();
                    return; // Stop the loop
                }
                commentsCharged = true;
            }
            // --- END NEW ---
            
            // Format output to match dataset_schema.json
            const videoId = videoUrl.split('v=')[1]?.split('&')[0] || null;
            const output = {
                videoId: videoId,
                title: result.metadata.title,
                channel: result.metadata.channel,
                views: result.metadata.views,
                likes: result.metadata.likes,
                captions: JSON.stringify(result.captions),
                transcriptMerged: result.transcriptMerged,
                comments: JSON.stringify(result.comments || []),
                // --- UPDATED CHARGE STATUS ---
                _chargeStatus: `Metadata: ${metadataCharged ? 'Charged' : 'Failed'}, Captions: ${captionsCharged ? 'Charged' : 'Not Found'}, Comments: ${commentsCharged ? 'Charged' : 'Not Found'}`
            };
            await Actor.pushData(output);
        }
    }

    log.info('✅ Actor finished successfully.');
});