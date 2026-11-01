"""Shared download and file-writing helpers."""

import os
from http.client import HTTPException
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen

from pydantic import ValidationError

USER_AGENT = "radio-schedules (+https://github.com/esp32-si4732/radio-schedules)"


def format_error(error: Exception) -> str:
    """Keep validation messages and useful metadata, without documentation links."""
    if not isinstance(error, ValidationError):
        return str(error)
    messages = []
    for detail in error.errors(include_url=False, include_context=False):
        field = ".".join(map(str, detail["loc"]))
        message = detail["msg"].removeprefix("Value error, ")
        value = detail["input"]
        message += (
            f" [type={detail['type']}, input_value={value!r}, "
            f"input_type={type(value).__name__}]"
        )
        messages.append(f"{field}: {message}" if field else message)
    return "; ".join(messages)


def fetch(url, *, data=None):
    try:
        request = Request(url, data=data, headers={"User-Agent": USER_AGENT})
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
