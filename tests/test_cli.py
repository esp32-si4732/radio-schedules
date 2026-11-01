import pytest

from radio_schedules.cli import main


@pytest.mark.parametrize(
    "changes", [[], ["Changed D: Germany -> New name", "Added J: Japan"]]
)
def test_check_itu_output(monkeypatch, capsys, changes):
    from radio_schedules import itu

    monkeypatch.setattr(itu, "check", lambda: changes)
    assert main(["check", "itu"]) == int(bool(changes))
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

    def check():
        raise error

    monkeypatch.setattr(itu, "check", check)
    assert main(["check", "itu"]) == 1
    assert capsys.readouterr() == ("", str(error) + "\n")
