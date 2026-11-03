"""Bounded readiness polling for the local browser-test server."""
import time
from urllib.error import URLError
from urllib.request import urlopen

deadline = time.monotonic() + 20
while True:
    try:
        with urlopen('http://127.0.0.1:8000/api/health', timeout=1) as response:
            if response.status == 200:
                break
    except (URLError, TimeoutError):
        pass
    if time.monotonic() >= deadline:
        raise SystemExit('Local campaign server did not become ready within 20 seconds')
    time.sleep(.1)
