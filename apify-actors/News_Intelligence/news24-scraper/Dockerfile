# Use Apify’s official Python image (with Actor SDK preinstalled)
FROM apify/actor-python:3.12

# Install xvfb for running browsers in a virtual display
RUN apt-get update && apt-get install -y xvfb

# Tell the Apify base image to use xvfb
ENV APIFY_XVFB 1

# Copy your files into the container
COPY . ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only, lightweight)
RUN playwright install --with-deps chromium

# NOTE: The CMD line has been removed to use the base image's default.