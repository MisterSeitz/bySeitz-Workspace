2025-10-15T08:58:29.872Z ACTOR: Pulling container image of build Xp6X9mdBkxoZvXcfF from registry.
2025-10-15T08:58:29.875Z ACTOR: Creating container.
2025-10-15T08:58:29.943Z ACTOR: Starting container.
2025-10-15T08:58:31.225Z /usr/local/lib/python3.12/site-packages/playwright_stealth/stealth.py:6: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
2025-10-15T08:58:31.227Z   import pkg_resources
2025-10-15T08:58:31.347Z INFO:apify:Initializing actor...
2025-10-15T08:58:31.349Z INFO:apify:System info
2025-10-15T08:58:31.400Z INFO:httpx:HTTP Request: GET http://10.0.91.212:8010/v2/key-value-stores/IrOWugJay3YtRE9nb "HTTP/1.1 200 OK"
2025-10-15T08:58:31.456Z INFO:httpx:HTTP Request: GET http://10.0.91.212:8010/v2/key-value-stores/IrOWugJay3YtRE9nb/records/INPUT "HTTP/1.1 200 OK"
2025-10-15T08:58:31.457Z ERROR:apify:Actor failed with an exception
2025-10-15T08:58:31.459Z Traceback (most recent call last):
2025-10-15T08:58:31.461Z   File "/usr/src/app/src/main.py", line 170, in main
2025-10-15T08:58:31.463Z     proxy_password = Actor.apify_client._options.get('token')
2025-10-15T08:58:31.465Z                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2025-10-15T08:58:31.473Z AttributeError: 'function' object has no attribute 'get'
2025-10-15T08:58:31.475Z INFO:apify:Exiting actor