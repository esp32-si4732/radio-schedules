import pytest
from pydantic import ValidationError

from radio_schedules.cli import main
from radio_schedules.format import COLUMNS, Broadcast, FormatError, read, write


@pytest.fixture
def schedule(tmp_path):
    return tmp_path / "schedule.csv"


@pytest.mark.parametrize(
    "freq,hz", [("0.001", 1), ("11774.7", 11774700), ("4294967.295", 4294967295)]
)
def test_exact_frequency(freq, hz):
    assert Broadcast(freq=freq, station="Test").frequency_hz == hz


@pytest.mark.parametrize(
    "fields",
    [
        {"freq": "0"},
        {"freq": "4294967.296"},
        {"freq": "1.0000"},
        {"freq": "1e3"},
        {"freq": "+1"},
        {"freq": "١"},
        {"freq": ".1"},
        {"freq": "1."},
        {"freq": "1,000"},
        {"freq": ""},
        {"freq": 1000},
        {"station": " "},
        {"station": 'a"b'},
        {"station": "a;b"},
        {"notes": "a\nb"},
        {"notes": "a\rb"},
        {"notes": "a\0b"},
        {"notes": "a\tb"},
        {"notes": "a\x7fb"},
        {"notes": "a\x85b"},
        {"time": "2400-0100"},
        {"time": "0100-0100"},
        {"time": "1260-1300"},
        {"time": "0000-2401"},
        {"time": "800-0900"},
        {"days": "21"},
        {"days": "11"},
        {"days": "0"},
        {"days": "1-5"},
        {"flags": "ji"},
        {"flags": "ii"},
        {"flags": "J"},
        {"flags": "x"},
        {"from": "2025-02-29"},
        {"from": "2026-2-01"},
        {"from": "0000-01-01"},
        {"from": "2026-10-25", "to": "2026-10-24"},
        {"lat": "0"},
        {"lon": "0"},
        {"lat": "90.1", "lon": "0"},
        {"lat": "0", "lon": "-180.1"},
        {"lat": "+0", "lon": "0"},
        {"power": "0"},
        {"power": "-1"},
        {"azimuth": "360"},
        {"azimuth": "-1"},
        {"azimuth": "nd"},
        {"language": "English/"},
        {"language": "English/ French"},
        {"language": "English/English"},
    ],
)
def test_invalid_fields(fields):
    with pytest.raises(ValidationError):
        Broadcast.model_validate({"freq": "6000", "station": "Test", **fields})


def test_full_row_round_trip(schedule):
    row = Broadcast.model_validate(
        {
            "freq": "11774.7",
            "station": "  Example  Radio  ",
            "time": "2300-0100",
            "days": "1234567",
            "from": "2024-02-29",
            "to": "2024-02-29",
            "mode": "TEST",
            "language": "English/French",
            "location": "Australia",
            "site": "Sydney",
            "lat": "-90",
            "lon": "180",
            "power": "0.001",
            "azimuth": "ND",
            "target": "Pacific",
            "flags": "ij",
            "notes": "Café",
        }
    )
    write(schedule, [row])
    assert read(schedule) == [row]
    assert row.station == "Example  Radio"
    data = schedule.read_bytes()
    assert data.startswith(";".join(COLUMNS).encode())
    assert b"\r" not in data and data.endswith(b"\n")


def test_reader_optional_columns_and_line_endings(schedule):
    schedule.write_bytes(
        b"\xef\xbb\xbf\r\n station ;extra; freq \r\n Test ;ignored; 6000 \r\n\r\nOther;;7000"
    )
    rows = read(schedule)
    assert rows == [
        Broadcast(freq="6000", station="Test"),
        Broadcast(freq="7000", station="Other"),
    ]


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"\n \n",
        b"freq\n6000",
        b"Freq;station\n6000;Test",
        b"freq;station;station\n6000;A;B",
        b"freq;station;\n6000;Test;",
        b"freq;station\n6000;Test;",
        b"freq;station\n6000",
        b"freq;station\n7000;A\n6000;B",
        b"freq;station\n6000;\xff",
        b"freq;station\n6000;Test\r",
        b"freq;station\r6000;Test",
        b'freq;station;extra\n6000;Test;"quoted"',
        b"freq;station\n# comment",
        b"freq;station\n6000;Test\x00",
    ],
)
def test_invalid_file(schedule, content):
    schedule.write_bytes(content)
    with pytest.raises(FormatError):
        read(schedule)


def test_error_physical_line(schedule):
    schedule.write_text("\nfreq;station\n\n6000;A\n5000;B\n")
    with pytest.raises(FormatError, match=r":5:.*ascending"):
        read(schedule)


def test_writer_sorts_without_deduplicating(schedule):
    rows = [
        Broadcast(freq=f, station=s)
        for f, s in [("10", "Z"), ("2", "A"), ("10", "A"), ("10", "A")]
    ]
    write(schedule, rows)
    assert [(r.freq, r.station) for r in read(schedule)] == [
        ("2", "A"),
        ("10", "A"),
        ("10", "A"),
        ("10", "Z"),
    ]


def test_reader_equal_frequency_order_is_unrestricted(schedule):
    schedule.write_text("freq;station\n10;Z\n10.000;A\n")
    assert len(read(schedule)) == 2


def test_writer_validates_before_overwriting(schedule):
    schedule.write_text("original")
    invalid = Broadcast.model_construct(freq="6000", station="", days="bad")
    with pytest.raises(ValidationError):
        write(schedule, [invalid])
    assert schedule.read_text() == "original"


def test_zero_coordinates_and_bearing():
    assert Broadcast(
        freq="6000", station="A", lat="0", lon="0", azimuth="0", time="0000-2400"
    )


def test_cli(schedule, capsys):
    schedule.write_text("freq;station\n6000;Example\n")
    assert main(["validate", str(schedule)]) == 0
    assert "valid (1 rows)" in capsys.readouterr().out
    schedule.write_text("freq;station\ninvalid;Example\n")
    assert main(["validate", str(schedule)]) == 1
    assert ":2:" in capsys.readouterr().err
    assert main(["validate", str(schedule.with_suffix(".missing"))]) == 1


def test_header_only(schedule):
    write(schedule, [])
    assert read(schedule) == []


def test_maximum_length_boundaries_round_trip(schedule):
    row = Broadcast.model_validate(
        {
            "freq": "0006000.000",
            "station": "Test",
            "time": "0000-2400",
            "days": "1234567",
            "from": "0001-01-01",
            "to": "9999-12-31",
            "lat": "-90.00000000",
            "lon": "-180.0000000",
            "azimuth": "359",
            "flags": "ij",
        }
    )
    write(schedule, [row])
    assert read(schedule) == [row]


@pytest.mark.parametrize(
    "fields",
    [
        {"freq": "000006000.000"},
        {"lat": "-90.000000000", "lon": "0"},
        {"lat": "0", "lon": "-180.00000000"},
        {"azimuth": "0000"},
        {"flags": "ijklmnopq"},
        {"time": "0000-24000"},
        {"days": "12345677"},
        {"from": "10000-01-01"},
        {"to": "10000-01-01"},
    ],
)
def test_column_length_limits(fields):
    with pytest.raises(ValidationError, match="must not exceed"):
        Broadcast.model_validate({"freq": "6000", "station": "Test", **fields})


@pytest.mark.parametrize("azimuth", ["0.5", "1.0", "90.0", "359.5"])
def test_azimuth_requires_integer_notation(azimuth):
    with pytest.raises(ValidationError):
        Broadcast(freq="6000", station="Test", azimuth=azimuth)


def test_length_limits_apply_after_trimming(schedule):
    schedule.write_text(
        "freq;station;lat;lon\n 4294967.295 ;Test; -90.00000000 ; -180.0000000 \n"
    )
    (row,) = read(schedule)
    assert row.freq == "4294967.295" and row.lon == "-180.0000000"


def test_reader_rejects_overlong_numeric_field(schedule):
    schedule.write_text("freq;station\n000006000.000;Test\n")
    with pytest.raises(FormatError, match="must not exceed 11"):
        read(schedule)


@pytest.mark.parametrize("mode", ["HFDL", "QPSK", "PWPM", "TEST"])
def test_four_byte_modes_round_trip(schedule, mode):
    row = Broadcast(freq="6000", station="Test", mode=mode)
    write(schedule, [row])
    assert read(schedule) == [row]


@pytest.mark.parametrize("mode", ["ABCDE", "HD Radio", "QPSK 1500bd"])
def test_overlong_modes_are_rejected(schedule, mode):
    schedule.write_text(f"freq;station;mode\n6000;Test;{mode}\n")
    with pytest.raises(FormatError, match="must not exceed 4"):
        read(schedule)


def test_station_limit_counts_utf8_bytes(schedule):
    row = Broadcast(freq="6000", station="é" * 20)
    write(schedule, [row])
    assert read(schedule) == [row]
    schedule.write_text("freq;station\n6000;" + "é" * 20 + "x\n")
    with pytest.raises(FormatError, match="must not exceed 40"):
        read(schedule)
