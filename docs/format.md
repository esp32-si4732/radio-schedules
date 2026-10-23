# Radio schedule CSV format

Version 1 (proposed). A human-editable schedule CSV format for EiBi, AOKI, and HFCC exports. Exporters normalize source-specific rules; receivers choose their own binary storage format.

## Syntax

- UTF-8, semicolon-delimited, one physical line per broadcast interval and transmitter site. Writers use LF without a BOM; readers accept LF/CRLF, an initial UTF-8 BOM, and an unterminated final line. Ignore blank lines; comments are unsupported.
- The first non-empty line is the header. Names are lowercase, case-sensitive, non-empty, and unique. Match columns by name, in any order; ignore unknown columns. Only `freq` and `station` are required.
- Every row has the header's field count. Preserve empty fields, including trailing ones. An omitted optional column means the same as an empty value.
- Trim surrounding ASCII spaces; preserve internal spaces. Writers should omit surrounding spaces.
- No quoting, escaping, or multiline values. Semicolons, double quotes, and control characters (including CR, LF, and NUL) are forbidden inside values; exporters replace them with spaces or suitable punctuation. Values are plain text, not HTML; escape them for web display.
- Numbers use ASCII digits. Decimals match `[0-9]+(\.[0-9]+)?`; only coordinates allow a leading minus. No plus signs, exponents, separators, or unit suffixes.

## Columns

The table gives the recommended order. Optional columns may be omitted. Maximum lengths are UTF-8 bytes after trimming surrounding ASCII spaces, including signs and decimal points but excluding delimiters, line endings, and string terminators. Numeric, date, weekday, and flag fields use ASCII syntax, so their byte and character counts are identical. A dash means no format-wide length limit.

| Column | Value | Empty/omitted | Max bytes |
|---|---|---|---:|
| `freq` | Positive kHz, up to 3 decimal places | Invalid | 11 |
| `time` | UTC `HHMM-HHMM` | `0000-2400` | 9 |
| `days` | Distinct ascending digits: `1`=Mon … `7`=Sun | Every day | 7 |
| `from` | First broadcast-start date, `YYYY-MM-DD` | No lower limit | 10 |
| `to` | Last broadcast-start date, `YYYY-MM-DD` | No upper limit | 10 |
| `mode` | Mode/system abbreviation, e.g. `AM`, `USB`, `DRM`, `HFDL` | Unknown | 4 |
| `station` | Station/service name | Invalid | 40 |
| `language` | Readable language name(s), separated by `/` | Unknown | — |
| `location` | Readable transmitter country, territory, or region name | Unknown | — |
| `site` | Transmitter-site name | Unknown | — |
| `lat` | Transmitter-site WGS 84 latitude, -90..90 decimal degrees | Unknown | 12 |
| `lon` | Transmitter-site WGS 84 longitude, -180..180 decimal degrees | Unknown | 12 |
| `power` | Positive kW, decimals allowed | Unknown | — |
| `azimuth` | Integer degrees clockwise from true north, `0..359`, or `ND` | Unknown | 3 |
| `target` | Readable target-region description | Unknown | — |
| `flags` | Single-letter flags: `i`=irregular/approximate, `j`=jammed | No flags | 8 |
| `notes` | Plain-text source annotations | No notes | — |

`flags` is a set of distinct lowercase letters, written together in alphabetical order without separators, e.g. `ij`. The 8-byte limit reserves capacity for future flags; it does not make additional flags valid. Only `i` and `j` are defined; other letters are reserved and invalid in this version. An empty field means no reported flags.

`freq` must convert exactly to integer Hz in `1..4294967295`. For example, `11774.7` = 11,774,700 Hz. Parse without floating point by padding the fractional part to three digits and computing `integer * 1000 + fraction`. The maximum, `4294967.295` kHz, needs 11 characters. Receivers may reject or hide frequencies outside their tuning range.

`mode` accepts a plain-text mode/system abbreviation of at most 4 UTF-8 bytes under the text rules above. Prefer consistent spellings: `AM`, `USB`, `LSB`, `CW`, `FM`, `DRM`, `HFDL`, `RTTY`. This list is not exhaustive; an unrecognized abbreviation within the length limit is valid and may be displayed even when the receiver cannot decode it. Receivers compare mode names ignoring ASCII letter case; other spelling aliases are not implied.

Adapters must use explicit mappings for longer source mode names, never truncate them. Aoki uses `HDR` for `HD Radio`, `PWPM` for `PWM/PM`, and `QPSK` for `QPSK 1500bd`. Original mode descriptions and the baud rate are omitted from notes to keep exports compact. These labels identify the source system and do not imply that a receiver supports decoding it.

Station, location, language, and site values are readable names, not ITU or ISO codes. Use source-provided names or expand codes using that source's definitions; no common naming registry is required. `location` describes the transmitter's country, territory, or region; `site` identifies the specific transmitting site. Never substitute broadcaster location or target region for an unknown transmitter location.

`station` is limited to 40 UTF-8 bytes. Exporters may apply source-specific abbreviations, then shorten remaining overlong names at a word boundary with a trailing `…` (3 UTF-8 bytes included in the limit). If a single word cannot fit, shorten it at a UTF-8 character boundary. Readers reject overlong names rather than silently changing them. Do not copy the original name into notes merely because it was shortened. Shortened names are display labels, not unique identifiers; never merge broadcasts based on a shortened name.

`language` contains names such as `English`, `French`, or `English/French`. Separate multiple names with `/`, without surrounding spaces or duplicates; their order does not specify airtime. Preserve source naming distinctions rather than forcing uncertain equivalences. Exporters must distinguish language lists from source code/name pairs and aliases, and omit empty list components: `kht/Khamti` becomes `Khamti`, while `English/French` remains a list.

The limits above are mandatory for readers and writers. Reject overlong values; do not truncate or round numeric or scheduling fields to make them fit. Coordinates must fit within 12 bytes: this accommodates the full latitude and longitude ranges with seven decimal places, including `-180.0000000`. More fractional digits are allowed when the complete value still fits. Azimuths accept only integer notation or `ND`; decimal notation such as `90.0` is invalid.

Other fields have no format-wide length limit. Constrained receivers/export profiles must document any additional limits. Only descriptive fields (`station`, `location`, `language`, `site`, `target`, `notes`) may be truncated, at UTF-8 boundaries. Reject or skip rows that exceed other limits; never interpret an overflowing line's remainder as another record.

### Scheduling semantics

- Start is inclusive; end is exclusive. Hours are `00..23`, minutes `00..59`; only an end may be `2400`. Equal endpoints are invalid; `0000-2400` is all day.
- An end earlier than its start crosses midnight. Weekdays and dates apply to the **UTC start date**: Friday `2300-0100` continues until Saturday 01:00, even if Friday is the final `to` date. After-midnight searches must also consider intervals starting on the previous date.
- `days=12345` means weekdays, `67` weekends, `1234567` daily. No weekday names, ranges, bitmask integers, or special rules are accepted.
- Dates are valid Gregorian dates with four-digit years, inclusive, and non-recurring. If both are present, `from <= to`.
- Flag `i` means **possibly on air** within the supplied restrictions; it does not override them. For unknown timing components, leave those fields empty and set `i`, retaining all known restrictions. Without `i`, empty timing fields mean unrestricted operation as defined above. Ordinary schedules are not guarantees of transmission or reception.
- Flag `j` means the broadcast is reported jammed, not inactive or itself a jammer. It does not change the schedule restrictions.

### Transmitter data and notes

Transmitter data is inline: repeat `location`, `site`, `lat`, `lon`, `power`, and `azimuth` in each applicable row. Exporters resolve source transmitter IDs and join any separate site tables before writing; receivers need no external transmitter table. Include known values; leave unknown values empty. Empty fields never inherit values from previous rows.

Supply both coordinates or neither; south/west are negative. Zero is a valid coordinate/bearing, not a missing-value marker. Power and azimuth belong to the broadcast, not necessarily the whole site. Azimuth is the main-beam bearing; exporters resolve source antenna/slew conventions. `ND` means non-directional. Leave uncertain values empty. These columns may be ignored for basic tuning.

`notes` may retain last-heard dates, test status, or other source details. The same text restrictions apply: no semicolons, double quotes, or line breaks. Notes do not override structured fields; export known scheduling restrictions in the time/day/date fields rather than only in prose.

## Export rules

- Exclude explicitly inactive entries; distinguish them from jammed broadcasts and jammers. Retain jammed broadcasts with flag `j`. Normalize frequencies, UTC times, and weekday numbering.
- Resolve seasons and DST into dated intervals; do not export persistence codes requiring receiver-side interpretation. Preserve known source validity limits. Publication and “last heard” dates are not broadcast validity bounds.
- Expand rules such as “first Sunday” into single-date rows (`from=to`) within the known validity period where practical. Otherwise retain trustworthy restrictions and set `flags=i`; never imply definite daily operation.
- Emit separate rows for distinct known transmitter sites carrying a broadcast, with each site's applicable timing, coordinates, power, and azimuth. Named alternative sites with individual coordinate pairs may also be expanded; retain an alternative-site qualification and the shared source transmitter code in every row's `notes`. These rows represent possible locations, not confirmation that all sites transmit simultaneously. Leave unresolved site details empty and preserve the source information in `notes`.
- Preserve distinct broadcasts sharing a frequency; frequency or station alone is not a deduplication key.
- Rows must be sorted by ascending numeric frequency (nondecreasing: equal frequencies are allowed). This requirement applies to all files, including hand-written ones. Validators must reject the entire file if a row's frequency is lower than the preceding row's frequency. Within equal frequencies, prefer start time and station name order; these tie-breakers are not validity requirements.

## Examples

Illustrative entries, not actual schedules. Minimal hand-written file:

```csv
freq;time;station
6070;0800-0900;Example Radio
9670;1800-1900;Another Station
```

Recommended columns, including an overnight and an irregular broadcast:

```csv
freq;time;days;from;to;mode;station;language;location;site;flags
6000;;;;;AM;Example Station;;;;i
7200;2300-0100;1234567;;;USB;Example Service;English;Australia;Sydney;
9700;0900-1000;12345;2026-03-29;2026-10-25;AM;Example Radio;English;United Kingdom;Woofferton;
```

Single-date broadcast with inline transmitter data:

```csv
freq;time;from;to;mode;station;language;location;site;lat;lon;power;azimuth
9700;0900-1000;2026-10-25;2026-10-25;AM;Example Radio;English;United Kingdom;Woofferton;52.31667;-2.81667;100;ND
```

Digital mode and combined flags:

```csv
freq;mode;station;flags;notes
6000;AM;Example Radio;ij;Test transmission
10081;HFDL;Example Data Station;;Last heard 2026-10-20
```

## Validation and compatibility

Invalid headers and out-of-order frequencies invalidate the file. Invalid rows include missing required values, wrong field counts, invalid UTF-8, or invalid field values. Reject the file or skip bad rows with a diagnostic; never turn malformed restrictions into unrestricted schedules. Unknown/unsupported modes must not be silently treated as playable in another mode; identification-only use is permitted.

There is no version preamble. Additions may introduce optional columns but must preserve existing meanings. Changes to units, defaults, or scheduling semantics require a separately identified format.
