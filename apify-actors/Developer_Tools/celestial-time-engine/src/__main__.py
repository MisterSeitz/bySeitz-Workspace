import asyncio
import logging

from apify.log import ActorLogFormatter
from .main import main

if __name__ == '__main__':
    # Set up logging as recommended in Apify docs
    handler = logging.StreamHandler()
    handler.setFormatter(ActorLogFormatter())

    apify_logger = logging.getLogger('apify')
    apify_logger.setLevel(logging.DEBUG)
    apify_logger.addHandler(handler)
    
    # Run the main async function
    asyncio.run(main())