# Use cases

Possible applications of the [radio schedule CSV format](format.md). Optional metadata enables richer features; applications can also use minimal schedules.

- **Station identification:** Show candidate stations for a tuned frequency, filtered by UTC time, weekday, and validity dates. Preserve multiple matches.
- **On-air browser:** List broadcasts scheduled now or later, searchable by station, language, frequency, mode, transmitter location, site, or target.
- **Tune from a list:** Select a broadcast on a receiver, desktop application, or web interface and tune its frequency using a supported mode.
- **Scheduled scanning:** Scan frequencies expected to be active, restricted to the receiver's tuning range and supported modes.
- **Listening plans and reminders:** Build personal schedules, show times in the listener's timezone, and notify them before a broadcast starts.
- **Automated recording:** Feed dated broadcast intervals to an SDR recorder, with application-defined recording margins and tuner-conflict handling.
- **Transmitter maps:** Plot known sites, calculate distance and bearing from a listener's location, and show reported power and antenna direction.
- **Reception planning:** Supply frequency, timing, site coordinates, power, and azimuth to a propagation tool alongside its required environmental data.
- **Reception logging:** Suggest station and transmitter details for a log entry from the observed frequency and reception time.
- **Offline receiver databases:** Download or copy a schedule, then parse it incrementally into a device-specific binary format for fast local lookup.
- **Shared source adapters:** Convert EiBi, AOKI, and HFCC once into a common format that multiple receiver applications can consume.
- **Combined schedules:** Merge converted datasets, compare overlapping entries, and apply explicit conflict and deduplication rules while retaining distinct broadcasts on the same frequency.
- **Custom exports:** Produce subsets for a language, band, date range, region, or receiver capability; omit optional columns a device does not need.
- **Hand-written schedules:** Maintain a small station list or event schedule in a text editor or spreadsheet configured for the format's CSV rules.
- **Schedule updates and archives:** Distribute replaceable files, retain dated snapshots, and compare releases for changed frequencies, times, or sites.
- **Data quality checks:** Validate fields and flag suspicious overlaps, inconsistent site metadata, or source conversion errors before distribution.
- **Schedule analysis:** Summarize listed airtime by language, band, mode, transmitter location, or target, accounting for overlapping records.

Schedules describe expected operation, not confirmed reception. Applications should distinguish irregular/approximate entries (`i`) and reported jamming (`j`). Maps and propagation tools need available transmitter metadata; missing values must not be guessed. Provenance, stable record IDs, reception reports, and recording settings belong to the consuming application or accompanying metadata, rather than this schedule CSV format.
