# Amazon AI Product Intelligence - Dockerfile

# Use a slim Python image
FROM python:3.11-slim

# Install system dependencies needed by Playwright/Chromium
# Removed deprecated libgconf-2-4
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        libnss3 \
        libatk-bridge2.0-0 \
        libdrm2 \
        libgbm1 \
        libgtk-3-0 \
        libasound2 \
        xvfb \
        procps \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /usr/src/app

# Copy requirements and install python packages
COPY requirements.txt .
# Use 'pip install' once, relying on the updated requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium)
# These steps will now execute successfully because the Python 'playwright' module is installed above
RUN python3 -m playwright install-deps
RUN python3 -m playwright install chromium

# Copy the rest of the application files
COPY . .

# Set environment variable for Apify (optional, but good practice)
# FIX: Increased ACTOR_MEMORY_MB to reduce 'Page crashed' errors during concurrent fetches.
ENV ACTOR_MEMORY_MB=4096 

# Execute the 'src' directory as a Python module, which runs src/__main__.py
CMD ["python3", "-m", "src"]