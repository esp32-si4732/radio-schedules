from http.client import IncompleteRead
from io import BytesIO
from urllib.error import URLError

import pytest

from radio_schedules import utils


def test_fetch(monkeypatch):
    def urlopen(request, timeout):
        assert request.full_url == "https://example.com/table"
        assert request.get_header("User-agent") == utils.USER_AGENT
        assert timeout == 30
        return BytesIO(b"source data")

    monkeypatch.setattr(utils, "urlopen", urlopen)
    assert utils.fetch("https://example.com/table") == b"source data"


@pytest.mark.parametrize("error", [URLError("unavailable"), IncompleteRead(b"", 10)])
def test_fetch_failure(monkeypatch, error):
    def urlopen(*args, **kwargs):
        raise error

    monkeypatch.setattr(utils, "urlopen", urlopen)
    with pytest.raises(OSError, match="could not download https://example.com/table"):
        utils.fetch("https://example.com/table")
