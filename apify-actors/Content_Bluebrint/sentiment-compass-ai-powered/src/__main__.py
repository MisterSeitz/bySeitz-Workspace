# src/__main__.py

from .main import main
import asyncio
from apify import Actor

# This code block initializes the Actor environment correctly before running main().
asyncio.run(Actor.main(main))