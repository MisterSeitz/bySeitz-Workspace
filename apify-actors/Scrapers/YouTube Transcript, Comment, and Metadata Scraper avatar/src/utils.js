// src/utils.js
import { log } from 'apify';

/**
 * Sleep helper
 */
export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Retry wrapper with exponential backoff
 */
export async function withRetry(fn, retries = 3, baseDelay = 2000, label = 'task') {
    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            return await fn();
        } catch (err) {
            if (attempt >= retries) throw err;
            const delay = baseDelay * Math.pow(2, attempt - 1);
            log.warning(
                `⚠️ ${label} failed (attempt ${attempt}/${retries}): ${err.message}. Retrying in ${Math.round(delay / 1000)}s...`
            );
            await sleep(delay);
        }
    }
}

/**
 * Parse a timestamp like "01:23" or "1:02:05" into seconds
 */
export function parseTimestamp(ts) {
    if (!ts) return 0;
    const parts = ts.split(':').map(Number);
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return 0;
}

/**
 * Clean and merge transcript segments
 */
export function cleanTranscript(segments) {
    if (!segments || !segments.length) return { captions: [], transcriptMerged: '' };

    const cleaned = segments
        .filter((s) => s.text && typeof s.start === 'number')
        .sort((a, b) => a.start - b.start)
        .map((s) => ({
            start: Math.round(s.start * 100) / 100,
            text: s.text.replace(/\s+/g, ' ').trim(),
        }));

    const transcriptMerged = cleaned.map((c) => c.text).join(' ');
    return { captions: cleaned, transcriptMerged };
}