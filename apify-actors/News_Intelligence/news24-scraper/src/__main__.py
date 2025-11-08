import asyncio
from .main import main

# This is the new entrypoint that calls the main function from your script.
if __name__ == '__main__':
    asyncio.run(main())