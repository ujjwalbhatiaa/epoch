# epoch

A small CLI timestamp converter. Convert between Unix timestamps and
human dates, across timezones, without reaching for a website.

```bash
epoch now --tz America/Edmonton
epoch to 1763596800 --tz Asia/Kolkata
epoch from "2026-11-20 08:00" --tz America/Edmonton
epoch diff 1763596800 "2026-11-21 08:00"
epoch add 1763596800 2d3h30m --tz UTC
```

## Commands

| Command | What it does |
| --- | --- |
| `epoch now [--tz ZONE] [--ms]` | Print the current time (Unix seconds, or milliseconds with `--ms`) |
| `epoch to <ts> [--tz ZONE]` | Unix timestamp → human date |
| `epoch from "<date>" [--tz ZONE]` | Human date → Unix timestamp |
| `epoch diff <a> <b> [--tz ZONE]` | Time between two moments (seconds + `1d 2h 30m` form) |
| `epoch add <moment> <duration> [--tz ZONE]` | Add a duration (`90s`, `2h30m`, `1d`, `1w`) to a moment |

Timestamps are Unix seconds; values with 13+ digits are read as
milliseconds. Dates are ISO 8601 (`YYYY-MM-DD`, with an optional time
and an optional UTC offset, e.g. `2026-11-20T08:00:00Z`). A date with
no offset is read in `--tz` (default: the local timezone), and `--tz`
takes any IANA zone name. Negative timestamps (before 1970) work, and
`diff`/`add` handle negative results.

## Run

Requires Python 3.9+ and nothing else — standard library only
(`datetime`, `zoneinfo`).

```bash
python3 epoch.py to 0 --tz UTC
# 0
# 1970-01-01T00:00:00+00:00
```

## Tests

```bash
python3 -m pytest
```
