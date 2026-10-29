from http.client import IncompleteRead
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

import pytest

from radio_schedules import utils
from radio_schedules.utils import write_bytes


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


def test_failed_replacement_preserves_destination_and_cleans_up(tmp_path, monkeypatch):
    destination = tmp_path / "export.csv"
    destination.write_bytes(b"previous")

    def replace(temporary, target):
        assert temporary.read_bytes() == b"complete export"
        assert target.read_bytes() == b"previous"
        raise OSError("cannot replace")

    monkeypatch.setattr(Path, "replace", replace)
    with pytest.raises(OSError, match="cannot replace"):
        write_bytes(destination, b"complete export")
    assert destination.read_bytes() == b"previous"
    assert list(tmp_path.iterdir()) == [destination]


def test_no_overwrite_preserves_file_created_during_download(tmp_path):
    destination = tmp_path / "source.csv"
    destination.write_bytes(b"local input")
    with pytest.raises(FileExistsError):
        write_bytes(destination, b"downloaded", overwrite=False)
    assert destination.read_bytes() == b"local input"
    assert list(tmp_path.iterdir()) == [destination]
