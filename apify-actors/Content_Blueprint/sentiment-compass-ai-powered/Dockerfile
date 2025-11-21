# Start from the base Python Apify image
FROM apify/actor-python:3.10

# Set the working directory
WORKDIR /usr/src/app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY . .

# Set the entrypoint to run the Actor
# This executes the main.py script as a Python module
CMD python3 -m src.main