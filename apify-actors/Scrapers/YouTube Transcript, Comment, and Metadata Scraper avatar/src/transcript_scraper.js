import playwright from 'playwright';
import { getSubtitles } from 'youtube-caption-extractor';
import { log } from 'apify';
// We no longer need axios
// import axios from 'axios'; 

export async function scrapeTranscript(videoUrl, lang = 'en') {
    log.info(`🎬 Scraping metadata for: ${videoUrl}`);

    const browser = await playwright.chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-dev-shm-usage']
    });

    const context = await browser.newContext({ locale: lang });
    const page = await context.newPage();

    let comments = [];
    let metadata = {};
    let captions = [];
    let merged = '';
    
    const videoIdMatch = videoUrl.match(/watch\?v=([a-zA-Z0-9_-]+)/);
    if (!videoIdMatch || !videoIdMatch[1]) {
        throw new Error('Could not parse Video ID from URL');
    }
    const videoID = videoIdMatch[1];

    try {
        // Go to the YouTube video page
        await page.goto(videoUrl, { waitUntil: 'networkidle', timeout: 60000 });
        log.info('✅ Page loaded and network is idle');

        // HANDLE COOKIE/CONSENT POPUP
        try {
            const rejectButtonSelector = '[aria-label*="Reject all"]';
            await page.waitForSelector(rejectButtonSelector, { state: 'visible', timeout: 5000 });
            await page.click(rejectButtonSelector);
            log.info('👋 Clicked "Reject all" on consent popup.');
        } catch (e) {
            log.info('No cookie consent popup found, continuing...');
        }
        
        // --- REVERTED: SCROLL DOWN TO LOAD COMMENTS ---
        log.info('... Scrolling down to load comments');
        try {
            await page.evaluate(async () => {
                for (let i = 0; i < 5; i++) { // Scroll 5 times
                    window.scrollBy(0, window.innerHeight * 2);
                    await new Promise(r => setTimeout(r, 1000)); // Wait for content to load
                }
            });
            // Use the 20-second timeout we set before
            await page.waitForSelector('ytd-comment-thread-renderer', { timeout: 20000 });
        } catch (e) {
            log.warning('Could not scroll or find comments, skipping...');
        }
        // --- END REVERT ---
        
        // --- REVERTED: SCRAPE COMMENTS FROM HTML ---
        try {
            comments = await page.$$eval('ytd-comment-thread-renderer', (threads) => {
                return threads.map(thread => {
                    const authorEl = thread.querySelector('#author-text');
                    const textEl = thread.querySelector('#content-text');
                    const likesEl = thread.querySelector('#vote-count-middle');
                    return {
                        author: authorEl ? authorEl.innerText.trim() : null,
                        text: textEl ? textEl.innerText.trim() : null,
                        likes: likesEl ? (likesEl.innerText.trim() || '0') : '0',
                    };
                }).filter(c => c.text); // Only return comments that have text
            });
            log.info(`✅ Found ${comments.length} comments.`);
        } catch (e) {
            log.warning(`Could not scrape comments: ${e.message}`);
        }
        // --- END REVERT ---
        
        // --- METADATA & TOKEN EXTRACTION ---
        await page.waitForSelector('h1 yt-formatted-string', { timeout: 15000 });

        metadata = await page.evaluate(() => {
            const title =
                document.querySelector('h1 yt-formatted-string')?.innerText ||
                document.title || '';
            const channel =
                document.querySelector('ytd-channel-name a')?.innerText || '';
            const uploadDate =
                document.querySelector('#info-strings yt-formatted-string')?.innerText || '';
            const views =
                document.querySelector('.view-count')?.innerText || '';
            
            let likes = '';
            
            try {
                // 1. Find the script tag with ytInitialData
                const scripts = Array.from(document.querySelectorAll('script'));
                const dataScript = scripts.find(s => s.innerText.includes('var ytInitialData = '));
                
                if (dataScript) {
                    // 2. Extract and parse the JSON blob
                    const match = dataScript.innerText.match(/var ytInitialData = ({.*?});/);
                    if (match && match[1]) {
                        const ytInitialData = JSON.parse(match[1]);
                        
                        // 3. Find the like button data (recursively)
                        function findLikeButton(obj) {
                            if (obj && typeof obj === 'object') {
                                if (obj.buttonViewModel && obj.buttonViewModel.iconName === 'LIKE') {
                                    return obj.buttonViewModel;
                                }
                                for (const key in obj) {
                                    if (obj.hasOwnProperty(key)) {
                                        const result = findLikeButton(obj[key]);
                                        if (result) return result;
                                    }
                                }
                            }
                            return null;
                        }
                        
                        const likeButton = findLikeButton(ytInitialData);
                        if (likeButton) {
                            likes = likeButton.title || '';
                        }
                    }
                }
            } catch (e) {
                // Could not parse, will remain blank
            }

            const description =
                document.querySelector('#description yt-formatted-string')?.innerText ||
                document.querySelector('meta[name="description"]')?.content || '';
            
            return { title, channel, uploadDate, views, likes, description };
        });
        
        // We are done with the browser now
        await browser.close();
        log.info(`✅ Metadata scraped for: ${metadata.title}`);

        // --- TRANSCRIPT LOGIC ---
        log.info('... Fetching transcript using youtube-caption-extractor');
        try {
            captions = await getSubtitles({
                videoID: videoID,
                lang: lang
            });
            merged = captions.map((c) => c.text).join(' ');
            log.info(`✅ Captions fetched: ${captions.length} segments`);
        } catch (transcriptError) {
            log.warning(`⚠️ Could not fetch transcript: ${transcriptError.message}`);
        }

        return {
            videoUrl,
            metadata,
            captions,
            transcriptMerged: merged || null,
            comments,
            source: 'hybrid-playwright+api'
        };

    } catch (err) {
        log.error(`❌ ${err.message}`);
        if (browser) await browser.close();
        return {
            videoUrl,
            metadata: {},
            captions: [],
            transcriptMerged: null,
            comments: [], 
            error: err.message
        };
    }
}