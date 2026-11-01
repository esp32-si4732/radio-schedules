from io import BytesIO

import pytest
from openpyxl import Workbook

from radio_schedules import itu


def workbook(rows, heading="Symbol", extra_sheet=False):
    book = Workbook()
    sheet = book.active
    sheet.append((heading, "Designation"))
    for row in rows:
        sheet.append(row)
    if extra_sheet:
        book.create_sheet("Extra")
    data = BytesIO()
    book.save(data)
    book.close()
    return data.getvalue()


def test_parse():
    assert itu.parse(
        workbook(
            [
                ("D", " Germany "),
                ("CG7", "Name & details"),
                ("CTI", "Côte d'Ivoire"),
            ]
        )
    ) == {"D": "Germany", "CG7": "Name & details", "CTI": "Côte d'Ivoire"}


@pytest.mark.parametrize(
    "rows,options,message",
    [
        pytest.param([], {}, "empty geographical table", id="empty"),
        pytest.param(
            [("D", "Germany")],
            {"heading": "Code"},
            "row 1: unrecognized table headings",
            id="headings",
        ),
        pytest.param([("D", "")], {}, "row 2: invalid table row", id="missing-name"),
        pytest.param(
            [("D", "Germany"), ("D", "Duplicate")],
            {},
            "row 3: duplicate code: D",
            id="duplicate",
        ),
        pytest.param(
            [("bad", "Name")], {}, "row 2: invalid table row", id="invalid-code"
        ),
        pytest.param(
            [("D", "Germany", "Extra")],
            {},
            "row 1: unrecognized table headings",
            id="extra-column",
        ),
        pytest.param(
            [("D", "Germany")],
            {"extra_sheet": True},
            "expected one worksheet",
            id="extra-sheet",
        ),
        pytest.param(
            [(123, "Name")], {}, "row 2: invalid table row", id="numeric-code"
        ),
        pytest.param([("D", "   ")], {}, "row 2: invalid table row", id="blank-name"),
        pytest.param(
            [("D", "Germany"), ("F", 123)],
            {},
            "row 3: invalid table row",
            id="numeric-name",
        ),
    ],
)
def test_invalid_workbook(rows, options, message):
    data = workbook(rows, **options)
    with pytest.raises(ValueError, match=message):
        itu.parse(data)


@pytest.mark.parametrize("kind", ["html", "truncated"])
def test_invalid_excel_file(kind):
    data = (
        b"<html>Unavailable</html>"
        if kind == "html"
        else workbook([("D", "Germany")])[:100]
    )
    with pytest.raises(ValueError, match="ITU: invalid Excel export"):
        itu.parse(data)


@pytest.mark.parametrize(
    "rows,expected",
    [
        pytest.param([("F", "France"), ("D", "Germany")], [], id="unchanged-reordered"),
        pytest.param(
            [("J", "Japan"), ("D", "New name")],
            ["Changed D: Germany -> New name", "Removed F: France", "Added J: Japan"],
            id="added-removed-changed",
        ),
    ],
)
def test_check(monkeypatch, capsys, rows, expected):
    original = {
        "D": ("Germany", "Short Germany", "DE"),
        "F": ("France", "France", "FR"),
    }
    monkeypatch.setattr(itu, "AREAS", original.copy())
    response = workbook(rows)
    calls = []

    def fetch(url, *, data=None):
        calls.append((url, data))
        return response

    monkeypatch.setattr(itu, "fetch", fetch)
    assert itu.check() == expected
    assert calls == [(itu.URL, b"viewCommand=Excel")]
    assert itu.AREAS == original
    assert capsys.readouterr() == ("", "")


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
