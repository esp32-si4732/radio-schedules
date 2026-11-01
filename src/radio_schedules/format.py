"""The schedule CSV format defined in docs/format.md."""

import re
import unicodedata
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .utils import format_error, write_bytes


def clean_text(value: str) -> str:
    if any(c in ';"' or unicodedata.category(c) == "Cc" for c in value):
        raise ValueError("quotes, semicolons and control characters are forbidden")
    return value.strip(" ")


Text = Annotated[str, AfterValidator(clean_text)]


def utf8_bytes(limit: int) -> AfterValidator:
    """Limit encoded bytes, rather than the character count used by max_length."""

    def validate(value: str) -> str:
        if len(value.encode("utf-8")) > limit:
            raise ValueError(f"must not exceed {limit} UTF-8 bytes")
        return value

    return AfterValidator(validate)


def decimal_number(value: str, *, signed: bool = False) -> Decimal:
    pattern = r"[0-9]+(?:\.[0-9]+)?"
    if not re.fullmatch(r"-?" + pattern if signed else pattern, value):
        raise ValueError("invalid decimal syntax")
    return Decimal(value)


def coordinate(limit: int) -> AfterValidator:
    def validate(value: str) -> str:
        if value and not -limit <= decimal_number(value, signed=True) <= limit:
            raise ValueError(f"coordinate must be in {-limit}..{limit}")
        return value

    return AfterValidator(validate)


class Broadcast(BaseModel):
    # Strings retain the format's exact numeric syntax and empty-field semantics.
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    freq: Annotated[Text, Field(min_length=1, max_length=11)]
    time: Annotated[Text, Field(max_length=9)] = ""
    days: Annotated[Text, Field(pattern=r"^1?2?3?4?5?6?7?$")] = ""
    from_date: Annotated[Text, Field(max_length=10)] = Field("", alias="from")
    to_date: Annotated[Text, Field(max_length=10)] = Field("", alias="to")
    mode: Annotated[Text, utf8_bytes(4)] = ""
    station: Annotated[Text, Field(min_length=1), utf8_bytes(40)]
    language: Text = ""
    location: Text = ""
    site: Text = ""
    lat: Annotated[Text, Field(max_length=12), coordinate(90)] = ""
    lon: Annotated[Text, Field(max_length=12), coordinate(180)] = ""
    power: Text = ""
    azimuth: Annotated[Text, Field(max_length=3)] = ""
    target: Text = ""
    flags: Annotated[Text, Field(pattern=r"^i?j?$")] = ""
    notes: Text = ""

    @field_validator("freq")
    @classmethod
    def frequency(cls, value):
        number = decimal_number(value)
        if len(value.partition(".")[2]) > 3 or not Decimal(
            "0.001"
        ) <= number <= Decimal("4294967.295"):
            raise ValueError("frequency must be an integer Hz in 1..4294967295")
        return value

    @field_validator("power")
    @classmethod
    def positive_power(cls, value):
        if value and decimal_number(value) <= 0:
            raise ValueError("power must be positive")
        return value

    @field_validator("azimuth")
    @classmethod
    def bearing(cls, value):
        if value in {"", "ND"}:
            return value
        if not re.fullmatch(r"[0-9]+", value) or int(value) >= 360:
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


def select_columns(columns=None, exclude_columns=None):
    """Resolve an export column selection without producing an invalid schema."""
    for names in (columns, exclude_columns):
        if names is not None:
            if not names or any(name not in COLUMNS for name in names):
                raise ValueError(
                    "column names must be selected from: " + ",".join(COLUMNS)
                )
            if len(names) != len(set(names)):
                raise ValueError("column names must be unique")
    selected = tuple(
        name
        for name in (COLUMNS if columns is None else columns)
        if name not in (exclude_columns or ())
    )
    if not {"freq", "station"} <= set(selected):
        raise ValueError("export requires freq and station columns")
    if ("lat" in selected) != ("lon" in selected):
        raise ValueError("select or exclude lat and lon together")
    return selected


class FormatError(ValueError):
    """An invalid schedule CSV file, including its path and physical line number."""


def read(path: str | Path) -> list[Broadcast]:
    path = Path(path)
    rows = []
    header = None
    previous = 0
    with path.open("rb") as file:
        for line_number, raw in enumerate(file, 1):
            try:
                # CR is accepted only as part of CRLF, not inside a value.
                if raw.endswith(b"\n"):
                    raw = raw[:-1].removesuffix(b"\r")
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
                    raise ValueError(
                        f"expected {len(header)} fields, got {len(fields)}"
                    )
                row = Broadcast.model_validate(
                    {key: value for key, value in zip(header, fields) if key in COLUMNS}
                )
                if row.frequency_hz < previous:
                    raise ValueError("frequencies must be in ascending order")
                previous = row.frequency_hz
                rows.append(row)
            except ValueError as exc:
                raise FormatError(f"{path}:{line_number}: {format_error(exc)}") from exc
    if header is None:
        raise FormatError(f"{path}: missing header")
    return rows


def write(path: str | Path, rows, *, columns=None) -> None:
    """Validate and sort all rows before writing the selected columns."""
    columns = select_columns(columns)
    rows = [Broadcast.model_validate(row.model_dump(by_alias=True)) for row in rows]
    rows.sort(key=lambda row: (row.frequency_hz, row.time or "0000-2400", row.station))
    lines = [";".join(columns)]
    for row in rows:
        values = row.model_dump(by_alias=True)
        lines.append(";".join(values[column] for column in columns))
    write_bytes(path, ("\n".join(lines) + "\n").encode("utf-8"))
