# Use Apify’s Playwright Chromium image (includes headless browser)
FROM apify/actor-node-playwright-chrome:20

# Copy dependency manifest and install first for layer caching
COPY package*.json ./
RUN npm install --omit=dev

# Copy the rest of the actor source
COPY . ./

# Set environment for Playwright headless and safer memory use
ENV PLAYWRIGHT_HEADLESS=true \
    NODE_ENV=production \
    APIFY_HEADLESS=true \
    APIFY_DISABLE_XVFB=true

# ✅ Force the run command directly here (bypasses any xvfb-run injection)
ENTRYPOINT ["node", "src/main.js"]