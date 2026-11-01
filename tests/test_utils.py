from http.client import IncompleteRead
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

import pytest

from radio_schedules import utils
from radio_schedules.utils import write_bytes


def test_format_validation_errors():
    from pydantic import ValidationError

    from radio_schedules.format import Broadcast

    with pytest.raises(ValidationError) as exc:
        Broadcast(freq="0", station="Test", power="0")
    assert utils.format_error(exc.value) == (
        "freq: frequency must be an integer Hz in 1..4294967295 "
        "[type=value_error, input_value='0', input_type=str]; "
        "power: power must be positive [type=value_error, input_value='0', input_type=str]"
    )


def test_format_model_error():
    from pydantic import ValidationError

    from radio_schedules.format import Broadcast

    with pytest.raises(ValidationError) as exc:
        Broadcast(freq="6000", station="Test", lat="0")
    message = utils.format_error(exc.value)
    assert message.startswith(
        "supply both coordinates or neither [type=value_error, input_value="
    )
    assert "'lat': '0'" in message
    assert message.endswith("input_type=dict]")
    assert "https://errors.pydantic.dev" not in message


def test_format_wrong_input_type():
    from pydantic import ValidationError

    from radio_schedules.format import Broadcast

    with pytest.raises(ValidationError) as exc:
        Broadcast(freq=6000, station="Test")
    assert utils.format_error(exc.value) == (
        "freq: Input should be a valid string "
        "[type=string_type, input_value=6000, input_type=int]"
    )


def test_format_plain_error():
    assert utils.format_error(ValueError("invalid header")) == "invalid header"


@pytest.mark.parametrize("data", [None, b"viewCommand=Excel"])
def test_fetch(monkeypatch, data):
    def urlopen(request, timeout):
        assert request.full_url == "https://example.com/table"
        assert request.get_header("User-agent") == utils.USER_AGENT
        assert request.data == data
        assert request.get_method() == ("GET" if data is None else "POST")
        assert timeout == 30
        return BytesIO(b"source data")

    monkeypatch.setattr(utils, "urlopen", urlopen)
    assert utils.fetch("https://example.com/table", data=data) == b"source data"


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
