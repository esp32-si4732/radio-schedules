import pytest

from radio_schedules.cli import main


@pytest.mark.parametrize(
    "changes", [[], ["Changed D: Germany -> New name", "Added J: Japan"]]
)
@pytest.mark.parametrize("refresh", [False, True])
def test_check_itu_output(monkeypatch, capsys, changes, refresh):
    from radio_schedules import itu

    def check(path, *, refresh=False):
        calls.append((path, refresh))
        return changes

    calls = []
    monkeypatch.setattr(itu, "check", check)
    assert main(
        ["check", "itu", "itu.xlsx", *(["--refresh"] if refresh else [])]
    ) == int(bool(changes))
    assert calls == [("itu.xlsx", refresh)]
    expected = (
        "\n".join(changes)
        if changes
        else f"ITU: no differences ({len(itu.AREAS)} entries)"
    )
    assert capsys.readouterr() == (expected + "\n", "")


@pytest.mark.parametrize(
    "error", [OSError("download failed"), ValueError("invalid workbook")]
)
def test_check_itu_error(monkeypatch, capsys, error):
    from radio_schedules import itu

    def check(path, *, refresh=False):
        raise error

    monkeypatch.setattr(itu, "check", check)
    assert main(["check", "itu", "itu.xlsx"]) == 1
    assert capsys.readouterr() == ("", str(error) + "\n")
