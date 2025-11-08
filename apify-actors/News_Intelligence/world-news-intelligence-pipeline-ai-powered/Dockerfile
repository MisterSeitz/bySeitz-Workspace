# First, specify the base Docker image.
FROM apify/actor-python:3.13

# Second, copy just requirements.txt into the Actor image.
COPY --chown=myuser:myuser requirements.txt ./

# 💡 FIX: Install dependencies directly to bypass the requirements.txt newline error 
# and eliminate all Playwright-related commands.
RUN PACKAGES="apify apify-client pydantic langgraph feedparser openai" \
    && echo "Python version:" \
    && python --version \
    && echo "Pip version:" \
    && pip --version \
    && echo "Installing dependencies:" \
    && pip install $PACKAGES \
    && echo "All installed Python packages:" \
    && pip freeze

# Next, copy the remaining files and directories with the source code.
COPY --chown=myuser:myuser . ./

# Use compileall to ensure the runnability of the Actor Python code.
RUN python3 -m compileall -q src/

# Specify how to launch the source code of your Actor.
CMD ["python3", "-m", "src"]