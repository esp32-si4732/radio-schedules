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
def test_check(tmp_path, monkeypatch, capsys, rows, expected):
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
    assert itu.check(tmp_path / "itu.xlsx") == expected
    assert calls == [(itu.URL, b"viewCommand=Excel")]
    assert itu.AREAS == original
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "codes,expected",
    [
        ("DE", []),
        (["SD", "SS"], []),
        ("ZZ", ["Invalid ISO mapping D: 'ZZ'"]),
        ("de", ["Invalid ISO mapping D: 'de'"]),
        ("DEU", ["Invalid ISO mapping D: 'DEU'"]),
        ("", ["Invalid ISO mapping D: ''"]),
        (["DE", "ZZ"], ["Invalid ISO mapping D: 'ZZ'"]),
        ([], ["Invalid ISO mapping D: empty code list"]),
        (["DE", "DE"], ["Invalid ISO mapping D: duplicate codes"]),
    ],
)
def test_check_iso_codes(tmp_path, monkeypatch, codes, expected):
    from radio_schedules.cli import main

    monkeypatch.setattr(itu, "AREAS", {"D": ("Germany", "Germany", codes)})
    path = tmp_path / "itu.xlsx"
    path.write_bytes(workbook([("D", "Germany")]))
    assert itu.check(path) == expected
    assert main(["check", "itu", str(path)]) == int(bool(expected))


def test_check_bundled_iso_codes(tmp_path):
    path = tmp_path / "itu.xlsx"
    path.write_bytes(workbook([(code, names[0]) for code, names in itu.AREAS.items()]))
    assert itu.check(path) == []


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


def test_local_input_is_reused_offline(tmp_path, monkeypatch):
    path = tmp_path / "itu.xlsx"
    data = workbook([("D", "Germany")])
    path.write_bytes(data)

    def fetch(*args, **kwargs):
        pytest.fail("local input must not trigger a download")

    monkeypatch.setattr(itu, "fetch", fetch)
    assert itu.prepare_input(path) == {"D": "Germany"}
    path.write_bytes(b"invalid local workbook")
    with pytest.raises(ValueError, match="invalid Excel export"):
        itu.prepare_input(path)


@pytest.mark.parametrize("refresh", [False, True])
def test_download_saves_valid_workbook(tmp_path, monkeypatch, refresh):
    path = tmp_path / "inputs" / "itu.xlsx"
    if refresh:
        path.parent.mkdir()
        path.write_bytes(workbook([("D", "Old name")]))
    data = workbook([("D", "Germany")])
    monkeypatch.setattr(itu, "fetch", lambda *args, **kwargs: data)
    assert itu.prepare_input(path, refresh=refresh) == {"D": "Germany"}
    assert path.read_bytes() == data


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("failure", ["download", "parse"])
def test_failed_download_preserves_local_file(tmp_path, monkeypatch, existing, failure):
    path = tmp_path / "itu.xlsx"
    original = workbook([("D", "Germany")])
    if existing:
        path.write_bytes(original)

    def fetch(*args, **kwargs):
        if failure == "download":
            raise OSError("download failed")
        return b"invalid workbook"

    monkeypatch.setattr(itu, "fetch", fetch)
    with pytest.raises((OSError, ValueError)):
        itu.prepare_input(path, refresh=existing)
    if existing:
        assert path.read_bytes() == original
    else:
        assert not path.exists()
