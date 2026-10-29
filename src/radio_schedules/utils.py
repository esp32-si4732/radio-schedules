"""Shared download and file-writing helpers."""

import os
from http.client import HTTPException
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen

USER_AGENT = "radio-schedules (+https://github.com/esp32-si4732/radio-schedules)"


def fetch(url):
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=30) as response:
            return response.read()
    except (OSError, HTTPException) as exc:
        raise OSError(f"could not download {url}: {exc}") from exc


def write_bytes(path, data, *, overwrite=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as file:
        temporary = Path(file.name)
        try:
            file.write(data)
            file.close()
            if overwrite:
                temporary.replace(path)
            else:
                os.link(temporary, path)
        finally:
            file.close()
            temporary.unlink(missing_ok=True)
