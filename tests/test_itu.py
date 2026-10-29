import pytest

from radio_schedules import itu
from radio_schedules.cli import main


def page(rows, count=None, heading="Symbol"):
    return (
        f"<table><tr><th>{heading}</th><th><button>Designation</button></th></tr>"
        + "".join(
            "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
            for row in rows
        )
        + f"</table>Number of symbols found = {len(rows) if count is None else count}"
    ).encode()


def test_parse():
    assert itu.parse(
        page(
            [
                ("D", " Germany "),
                ("CG7", "Name &amp; <b>details</b>"),
                ("CTI", "Côte d'Ivoire"),
            ]
        )
    ) == {"D": "Germany", "CG7": "Name & details", "CTI": "Côte d'Ivoire"}


@pytest.mark.parametrize(
    "data",
    [
        b"<html>Unavailable</html>",
        page([]),
        page([("D", "Germany")], count=2),
        page([("D", "Germany")], heading="Code"),
        page([("D", "")]),
        page([("D", "Germany"), ("D", "Duplicate")]),
        page([("bad", "Name")]),
        page([("D", "Germany", "Extra")]),
        page([("D", "Germany")]) + page([("F", "France")]),
        page([("D", "Germany")]).replace(b"</table>", b""),
    ],
)
def test_invalid_page(data):
    with pytest.raises(ValueError):
        itu.parse(data)


def test_cli_comparison(monkeypatch, capsys):
    monkeypatch.setattr(
        itu,
        "AREAS",
        {"D": ("Germany", "Short Germany", "DE"), "F": ("France", "France", "FR")},
    )
    calls = []

    def fetch(url):
        calls.append(url)
        return page([("F", "France"), ("D", "Germany")])

    monkeypatch.setattr(itu, "fetch", fetch)
    assert main(["check", "itu"]) == 0
    assert "no differences (2 entries)" in capsys.readouterr().out
    assert calls == [itu.URL]
    monkeypatch.setattr(
        itu, "fetch", lambda url: page([("D", "New name"), ("J", "Japan")])
    )
    assert main(["check", "itu"]) == 1
    assert capsys.readouterr().out.splitlines() == [
        "Changed D: Germany -> New name",
        "Removed F: France",
        "Added J: Japan",
    ]
    assert itu.AREAS == {
        "D": ("Germany", "Short Germany", "DE"),
        "F": ("France", "France", "FR"),
    }


@pytest.mark.parametrize(
    "error", [OSError("download failed"), ValueError("invalid page")]
)
def test_cli_error(monkeypatch, capsys, error):
    def fetch(url):
        raise error

    monkeypatch.setattr(itu, "fetch", fetch)
    assert main(["check", "itu"]) == 1
    assert str(error) in capsys.readouterr().err


def test_short_names_preserve_distinctions():
    assert itu.AREAS["D"] == ("Germany (Federal Republic of)", "Germany", "DE")
    for code in ("CHR", "BIO", "ICO", "FLK", "SXM", "GCA", "GCC"):
        official, short, _ = itu.AREAS[code]
        assert short == official
    assert itu.AREAS["COD"][1] != itu.AREAS["COG"][1]
    assert all(
        isinstance(names, tuple) and len(names) == 3 and all(names[:2])
        for names in itu.AREAS.values()
    )


@pytest.mark.parametrize(
    "area,iso",
    [
        ("D", "DE"),
        ("G", "GB"),
        ("USA", "US"),
        ("AFS", "ZA"),
        ("KOR", "KR"),
        ("KRE", "KP"),
        ("COD", "CD"),
        ("COG", "CG"),
        ("CHR", "CX"),
        ("BIO", "IO"),
        ("CVA", "VA"),
        ("PTC", "PN"),
        ("WAL", "WF"),
        ("ALS", "US"),
        ("HWA", "US"),
        ("SHN", "SH"),
        ("ASC", "SH"),
        ("TRC", "SH"),
        ("XGZ", "PS"),
        ("XWB", "PS"),
        ("XSD", ["SD", "SS"]),
        ("XBY", ["SD", "SS"]),
        ("XSP", ["CN", "TW", "VN", "PH", "MY"]),
        ("CG7", "CU"),
    ],
)
def test_iso_codes(area, iso):
    assert itu.AREAS[area][2] == iso


def test_area_and_parent_codes():
    expected = {
        "AMS": "TF",
        "AZR": "PT",
        "CNR": "ES",
        "CPT": "FR",
        "CRO": "TF",
        "DGA": "IO",
        "GCA": "GB",
        "GCC": "GB",
        "HWL": "UM",
        "JAR": "UM",
        "JON": "UM",
        "KER": "TF",
        "MDR": "PT",
        "MDW": "UM",
        "MRN": "ZA",
        "PAQ": "CL",
        "PHX": "KI",
        "PLM": "UM",
        "ROD": "MU",
        "SWN": "HN",
        "WAK": "UM",
    }
    assert {code: itu.AREAS[code][2] for code in expected} == expected
    assert all(iso for _, _, iso in itu.AREAS.values())
    assert {
        code for code, (_, _, iso) in itu.AREAS.items() if isinstance(iso, list)
    } == {
        "XBY",
        "XSD",
        "XSP",
    }


def test_check_returns_differences_without_printing(monkeypatch, capsys):
    monkeypatch.setattr(itu, "AREAS", {"D": ("Germany", "Germany", "DE")})
    monkeypatch.setattr(itu, "fetch", lambda url: page([("D", "New name")]))
    assert itu.check() == ["Changed D: Germany -> New name"]
    assert capsys.readouterr() == ("", "")
