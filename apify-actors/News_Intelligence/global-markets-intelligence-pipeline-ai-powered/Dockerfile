# First, specify the base Docker image.
FROM apify/actor-python:3.13

# Next, copy just requirements.txt and install the dependencies.
# This is the standard, robust method.
COPY --chown=myuser:myuser requirements.txt ./
RUN pip install -r requirements.txt

# Next, copy the remaining files and directories with the source code.
COPY --chown=myuser:myuser . ./

# Use compileall to ensure the runnability of the Actor Python code.
RUN python3 -m compileall -q src/

# Specify how to launch the source code of your Actor.
CMD ["python", "-m", "src.main"]