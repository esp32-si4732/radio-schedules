"""Shared download helper."""

from http.client import HTTPException
from urllib.request import Request, urlopen

USER_AGENT = "radio-schedules (+https://github.com/esp32-si4732/radio-schedules)"


def fetch(url):
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=30) as response:
            return response.read()
    except (OSError, HTTPException) as exc:
        raise OSError(f"could not download {url}: {exc}") from exc
