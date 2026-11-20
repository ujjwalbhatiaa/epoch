#!/usr/bin/env python3
"""epoch — a small command-line timestamp converter.

Convert between Unix timestamps and human dates, across timezones,
without reaching for a website or a calculator.

    epoch now [--tz America/Edmonton]
    epoch to 1763600000 [--tz Asia/Kolkata]
    epoch from "2026-11-20 08:00" [--tz America/Edmonton]
    epoch diff 1763600000 "2026-11-21 08:00"
    epoch add 1763600000 2d3h30m [--tz UTC]

Timestamps are Unix seconds by default; values with 13+ digits are read
as milliseconds. Dates are parsed as ISO 8601 (YYYY-MM-DD, with an
optional time and an optional UTC offset, e.g. 2026-11-20T08:00:00Z).
A date with no offset is read in --tz (default: the local timezone).
"""

import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSION = "0.1.0"

_DURATION_RE = re.compile(
    r"^(?P<sign>-)?"
    r"(?:(?P<weeks>\d+)w)?"
    r"(?:(?P<days>\d+)d)?"
    r"(?:(?P<hours>\d+)h)?"
    r"(?:(?P<minutes>\d+)m)?"
    r"(?:(?P<seconds>\d+)s)?$"
)


def fail(message):
    print(f"epoch: error: {message}", file=sys.stderr)
    raise SystemExit(2)


def load_tz(name):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        fail(f"unknown timezone: {name}")


def parse_timestamp(text):
    """Parse a Unix timestamp in seconds (or milliseconds) to a datetime."""
    try:
        value = int(text)
    except ValueError:
        try:
            value = int(float(text))
        except ValueError:
            fail(f"not a Unix timestamp: {text}")
    if abs(value) >= 10**12:  # milliseconds
        value = value // 1000
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        fail(f"timestamp out of range: {text}")


def parse_moment(text, tz):
    """Parse a timestamp or an ISO date into an aware datetime."""
    try:
        return parse_timestamp(text)
    except SystemExit:
        pass
    cleaned = text.strip()
    if cleaned.endswith(("Z", "z")):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        fail(
            f"not a timestamp or ISO date: {text} "
            "(try 1763600000 or 2026-11-20 08:00)"
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed


def parse_duration(text):
    """Parse '2d3h30m', '1w', '90s' or bare seconds into a timedelta."""
    cleaned = text.strip()
    if re.fullmatch(r"-?\d+", cleaned):
        return timedelta(seconds=int(cleaned))
    match = _DURATION_RE.match(cleaned)
    if not match or not any(
        match.group(part)
        for part in ("weeks", "days", "hours", "minutes", "seconds")
    ):
        fail(
            f"not a duration: {text} "
            "(try 90s, 2h30m, 1d, 1w, or a bare number of seconds)"
        )
    parts = {
        part: int(match.group(part) or 0)
        for part in ("weeks", "days", "hours", "minutes", "seconds")
    }
    delta = timedelta(**parts)
    return -delta if match.group("sign") else delta


def human_duration(delta):
    """Render a timedelta as '1w 2d 3h 4m 5s' (sign-aware)."""
    total = int(delta.total_seconds())
    sign = "-" if total < 0 else ""
    total = abs(total)
    weeks, total = divmod(total, 7 * 86400)
    days, total = divmod(total, 86400)
    hours, total = divmod(total, 3600)
    minutes, seconds = divmod(total, 60)
    parts = []
    for value, unit in (
        (weeks, "w"),
        (days, "d"),
        (hours, "h"),
        (minutes, "m"),
        (seconds, "s"),
    ):
        if value:
            parts.append(f"{value}{unit}")
    return sign + (" ".join(parts) if parts else "0s")


def show(moment, tz):
    """Print a moment as Unix seconds plus ISO 8601 in the given zone."""
    local = moment.astimezone(tz)
    print(int(moment.timestamp()))
    print(local.isoformat())


def cmd_now(args):
    tz = load_tz(args.tz) if args.tz else datetime.now().astimezone().tzinfo
    now = datetime.now(tz=tz)
    if args.ms:
        print(int(now.timestamp() * 1000))
    else:
        print(int(now.timestamp()))
    print(now.isoformat())


def cmd_to(args):
    tz = load_tz(args.tz) if args.tz else datetime.now().astimezone().tzinfo
    show(parse_timestamp(args.timestamp), tz)


def cmd_from(args):
    tz = load_tz(args.tz) if args.tz else datetime.now().astimezone().tzinfo
    moment = parse_moment(args.datetime, tz)
    print(int(moment.timestamp()))
    print(moment.astimezone(tz).isoformat())


def cmd_diff(args):
    tz = load_tz(args.tz) if args.tz else datetime.now().astimezone().tzinfo
    first = parse_moment(args.first, tz)
    second = parse_moment(args.second, tz)
    delta = second - first
    print(int(delta.total_seconds()))
    print(human_duration(delta))


def cmd_add(args):
    tz = load_tz(args.tz) if args.tz else datetime.now().astimezone().tzinfo
    moment = parse_moment(args.moment, tz)
    show(moment + parse_duration(args.duration), tz)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="epoch",
        description="Convert between Unix timestamps and human dates.",
    )
    parser.add_argument("--version", action="version", version=f"epoch {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_now = sub.add_parser("now", help="print the current time")
    p_now.add_argument("--tz", help="IANA timezone, e.g. America/Edmonton")
    p_now.add_argument("--ms", action="store_true", help="print milliseconds")
    p_now.set_defaults(func=cmd_now)

    p_to = sub.add_parser("to", help="timestamp -> human date")
    p_to.add_argument("timestamp", help="Unix seconds (13+ digits = milliseconds)")
    p_to.add_argument("--tz", help="IANA timezone to display in")
    p_to.set_defaults(func=cmd_to)

    p_from = sub.add_parser("from", help="human date -> timestamp")
    p_from.add_argument("datetime", help='ISO date, e.g. "2026-11-20 08:00"')
    p_from.add_argument("--tz", help="IANA timezone the date is in")
    p_from.set_defaults(func=cmd_from)

    p_diff = sub.add_parser("diff", help="time between two moments")
    p_diff.add_argument("first", help="timestamp or ISO date")
    p_diff.add_argument("second", help="timestamp or ISO date")
    p_diff.add_argument("--tz", help="IANA timezone for naive dates")
    p_diff.set_defaults(func=cmd_diff)

    p_add = sub.add_parser("add", help="add a duration to a moment")
    p_add.add_argument("moment", help="timestamp or ISO date")
    p_add.add_argument("duration", help="e.g. 2d3h30m, 1w, 90s")
    p_add.add_argument("--tz", help="IANA timezone for naive dates")
    p_add.set_defaults(func=cmd_add)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
