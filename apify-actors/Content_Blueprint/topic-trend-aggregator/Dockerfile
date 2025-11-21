# Use the correct, publicly available, stable Apify base image for Python 3.11
FROM apify/actor-python:3.11

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy all files (including requirements.txt and src/main.py)
COPY . .

# NOTE: The RUN pip install ... step is REMOVED from the build process.

# The command now explicitly installs requirements and then runs the script.
# This guarantees that pandas and apify-client are available.
CMD ["/bin/bash", "-c", "pip install --no-cache-dir -r requirements.txt && python src/main.py"]