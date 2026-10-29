"""The schedule CSV format defined in docs/format.md."""

import re
import unicodedata
from datetime import date
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .utils import write_bytes

MAX_LENGTHS = {
    "freq": 11,
    "time": 9,
    "days": 7,
    "from_date": 10,
    "to_date": 10,
    "mode": 4,
    "station": 40,
    "lat": 12,
    "lon": 12,
    "azimuth": 3,
    "flags": 8,
}


def clean_text(value: str) -> str:
    if any(c in ';"' or unicodedata.category(c) == "Cc" for c in value):
        raise ValueError("quotes, semicolons and control characters are forbidden")
    return value.strip(" ")


class Broadcast(BaseModel):
    # Strings retain the format's exact numeric syntax and empty-field semantics.
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    freq: str
    time: str = ""
    days: str = ""
    from_date: str = Field("", alias="from")
    to_date: str = Field("", alias="to")
    mode: str = ""
    station: str
    language: str = ""
    location: str = ""
    site: str = ""
    lat: str = ""
    lon: str = ""
    power: str = ""
    azimuth: str = ""
    target: str = ""
    flags: str = ""
    notes: str = ""

    @field_validator("*")
    @classmethod
    def text(cls, value, info):
        value = clean_text(value)
        limit = MAX_LENGTHS.get(info.field_name)
        if limit is not None and len(value.encode("utf-8")) > limit:
            raise ValueError(f"must not exceed {limit} UTF-8 bytes")
        return value

    @field_validator("freq", "station")
    @classmethod
    def required(cls, value):
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("freq", "lat", "lon", "power", "azimuth")
    @classmethod
    def number(cls, value, info):
        if not value or (info.field_name == "azimuth" and value == "ND"):
            return value
        pattern = (
            r"-?[0-9]+(?:\.[0-9]+)?"
            if info.field_name in {"lat", "lon"}
            else r"[0-9]+(?:\.[0-9]+)?"
        )
        if not re.fullmatch(pattern, value):
            raise ValueError("invalid decimal syntax")
        number = Decimal(value)
        match info.field_name:
            case "freq":
                if len(value.partition(".")[2]) > 3 or not Decimal(
                    "0.001"
                ) <= number <= Decimal("4294967.295"):
                    raise ValueError("frequency must be an integer Hz in 1..4294967295")
            case "lat" | "lon":
                limit = 90 if info.field_name == "lat" else 180
                if not -limit <= number <= limit:
                    raise ValueError(f"coordinate must be in {-limit}..{limit}")
            case "power":
                if number <= 0:
                    raise ValueError("power must be positive")
            case "azimuth":
                if not value.isascii() or not value.isdigit() or not 0 <= number < 360:
                    raise ValueError("azimuth must be an integer in 0..359 or ND")
        return value

    @field_validator("time")
    @classmethod
    def interval(cls, value):
        if value:
            clock = r"(?:[01][0-9]|2[0-3])[0-5][0-9]"
            if (
                not re.fullmatch(rf"{clock}-(?:{clock}|2400)", value)
                or value[:4] == value[5:]
            ):
                raise ValueError("expected HHMM-HHMM with distinct endpoints")
        return value

    @field_validator("from_date", "to_date")
    @classmethod
    def calendar_date(cls, value):
        if value:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError("expected YYYY-MM-DD")
            date.fromisoformat(value)
        return value

    @field_validator("days", "flags")
    @classmethod
    def ordered_set(cls, value, info):
        allowed = "1234567" if info.field_name == "days" else "ij"
        if any(c not in allowed for c in value) or value != "".join(sorted(set(value))):
            raise ValueError(f"expected distinct ascending characters from {allowed}")
        return value

    @field_validator("language")
    @classmethod
    def languages(cls, value):
        if value:
            parts = value.split("/")
            if any(not p or p != p.strip(" ") for p in parts) or len(parts) != len(
                set(parts)
            ):
                raise ValueError(
                    "language names must be distinct, non-empty and separated by /"
                )
        return value

    @model_validator(mode="after")
    def related_fields(self):
        if bool(self.lat) != bool(self.lon):
            raise ValueError("supply both coordinates or neither")
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValueError("from must not be later than to")
        return self

    @property
    def frequency_hz(self) -> int:
        whole, _, fraction = self.freq.partition(".")
        return int(whole.lstrip("0") or "0") * 1000 + int(fraction.ljust(3, "0"))


COLUMNS = tuple(field.alias or name for name, field in Broadcast.model_fields.items())


class FormatError(ValueError):
    """An invalid schedule CSV file, including its path and physical line number."""


def read(path: str | Path) -> list[Broadcast]:
    path = Path(path)
    rows = []
    header = None
    previous = 0
    lines = path.read_bytes().split(b"\n")
    for line_number, raw in enumerate(lines, 1):
        try:
            # CR is accepted only as part of CRLF, not inside a value.
            if raw.endswith(b"\r") and line_number < len(lines):
                raw = raw[:-1]
            line = raw.decode("utf-8-sig" if line_number == 1 else "utf-8")
            if not line.strip(" "):
                continue
            fields = [clean_text(value) for value in line.split(";")]
            if header is None:
                if any(not name or name != name.lower() for name in fields) or len(
                    fields
                ) != len(set(fields)):
                    raise ValueError(
                        "header names must be non-empty, lowercase and unique"
                    )
                if not {"freq", "station"} <= set(fields):
                    raise ValueError("header requires freq and station")
                header = fields
                continue
            if len(fields) != len(header):
                raise ValueError(f"expected {len(header)} fields, got {len(fields)}")
            row = Broadcast.model_validate(
                {key: value for key, value in zip(header, fields) if key in COLUMNS}
            )
            if row.frequency_hz < previous:
                raise ValueError("frequencies must be in ascending order")
            previous = row.frequency_hz
            rows.append(row)
        except ValueError as exc:
            raise FormatError(f"{path}:{line_number}: {exc}") from exc
    if header is None:
        raise FormatError(f"{path}: missing header")
    return rows


def write(path: str | Path, rows) -> None:
    """Validate and sort all rows before writing the recommended columns."""
    rows = [Broadcast.model_validate(row.model_dump(by_alias=True)) for row in rows]
    rows.sort(key=lambda row: (row.frequency_hz, row.time or "0000-2400", row.station))
    lines = [";".join(COLUMNS)]
    lines.extend(";".join(row.model_dump(by_alias=True).values()) for row in rows)
    write_bytes(path, ("\n".join(lines) + "\n").encode("utf-8"))
