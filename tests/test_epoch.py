import subprocess
import sys
import time
from datetime import datetime, timezone

import pytest

import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import epoch


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "epoch.py", *args],
        capture_output=True,
        text=True,
        cwd=__file__.rsplit("/", 1)[0] + "/..",
    )


# --- timestamp parsing ---

def test_parse_timestamp_epoch_zero():
    assert epoch.parse_timestamp("0") == datetime(1970, 1, 1, tzinfo=timezone.utc)


def test_parse_timestamp_known_value():
    # 2026-11-20 00:00:00 UTC
    assert epoch.parse_timestamp("1795132800") == datetime(
        2026, 11, 20, tzinfo=timezone.utc
    )


def test_parse_timestamp_milliseconds():
    assert epoch.parse_timestamp("1795132800000") == datetime(
        2026, 11, 20, tzinfo=timezone.utc
    )


def test_parse_timestamp_negative():
    assert epoch.parse_timestamp("-86400") == datetime(
        1969, 12, 31, tzinfo=timezone.utc
    )


def test_parse_timestamp_invalid():
    with pytest.raises(SystemExit):
        epoch.parse_timestamp("not-a-number")


def test_parse_timestamp_out_of_range():
    with pytest.raises(SystemExit):
        epoch.parse_timestamp("99999999999999999999")


# --- moment parsing ---

def test_parse_moment_iso_date_utc():
    tz = epoch.load_tz("UTC")
    assert epoch.parse_moment("2026-11-20", tz) == datetime(
        2026, 11, 20, tzinfo=timezone.utc
    )


def test_parse_moment_iso_with_zulu():
    tz = epoch.load_tz("UTC")
    assert epoch.parse_moment("1970-01-01T00:00:00Z", tz) == datetime(
        1970, 1, 1, tzinfo=timezone.utc
    )


def test_parse_moment_iso_with_offset():
    tz = epoch.load_tz("UTC")
    moment = epoch.parse_moment("2026-11-20T05:30:00+05:30", tz)
    assert int(moment.timestamp()) == 1795132800


def test_parse_moment_naive_uses_given_tz():
    tz = epoch.load_tz("America/Toronto")
    moment = epoch.parse_moment("2026-11-20 00:00", tz)
    # Toronto is UTC-5 in November (EST)
    assert moment.utcoffset().total_seconds() == -5 * 3600
    assert int(moment.timestamp()) == 1795132800 + 5 * 3600


def test_parse_moment_edmonton_round_trip():
    # Edmonton offset is taken from the system tzdata, whatever it says;
    # from -> to must round-trip exactly.
    tz = epoch.load_tz("America/Edmonton")
    moment = epoch.parse_moment("2026-11-20 08:00", tz)
    assert epoch.parse_moment(moment.isoformat(), tz) == moment


def test_parse_moment_timestamp_wins():
    tz = epoch.load_tz("UTC")
    assert epoch.parse_moment("1795132800", tz) == datetime(
        2026, 11, 20, tzinfo=timezone.utc
    )


def test_parse_moment_invalid():
    with pytest.raises(SystemExit):
        epoch.parse_moment("yesterday-ish", epoch.load_tz("UTC"))


def test_load_tz_invalid():
    with pytest.raises(SystemExit):
        epoch.load_tz("Mars/Olympus")


# --- durations ---

def test_parse_duration_units():
    assert epoch.parse_duration("90s").total_seconds() == 90
    assert epoch.parse_duration("2h30m").total_seconds() == 9000
    assert epoch.parse_duration("1w").total_seconds() == 7 * 86400
    assert epoch.parse_duration("1d2h3m4s").total_seconds() == 86400 + 7200 + 180 + 4


def test_parse_duration_bare_seconds():
    assert epoch.parse_duration("3600").total_seconds() == 3600


def test_parse_duration_negative():
    assert epoch.parse_duration("-1h").total_seconds() == -3600


def test_parse_duration_invalid():
    for bad in ("", "abc", "1x", "h", "1.5h", "2d3"):
        with pytest.raises(SystemExit):
            epoch.parse_duration(bad)


def test_human_duration():
    from datetime import timedelta

    assert epoch.human_duration(timedelta(seconds=0)) == "0s"
    assert epoch.human_duration(timedelta(seconds=90)) == "1m 30s"
    assert epoch.human_duration(timedelta(seconds=90061)) == "1d 1h 1m 1s"
    assert epoch.human_duration(timedelta(days=9)) == "1w 2d"
    assert epoch.human_duration(timedelta(seconds=-3661)) == "-1h 1m 1s"


# --- CLI end to end ---

def test_cli_now(capsys):
    before = int(time.time())
    epoch.main(["now", "--tz", "UTC"])
    after = int(time.time())
    out = capsys.readouterr().out.strip().splitlines()
    assert before <= int(out[0]) <= after
    assert out[1].startswith("20")  # ISO date in the 2000s


def test_cli_now_ms():
    result = run_cli("now", "--tz", "UTC", "--ms")
    assert result.returncode == 0
    assert len(result.stdout.strip().splitlines()[0]) == 13


def test_cli_to_zero():
    result = run_cli("to", "0", "--tz", "UTC")
    assert result.returncode == 0
    assert result.stdout.strip().splitlines() == [
        "0",
        "1970-01-01T00:00:00+00:00",
    ]


def test_cli_to_toronto():
    result = run_cli("to", "1795132800", "--tz", "America/Toronto")
    assert result.returncode == 0
    lines = result.stdout.strip().splitlines()
    assert lines[0] == "1795132800"
    assert lines[1] == "2026-11-19T19:00:00-05:00"


def test_cli_from_date():
    result = run_cli("from", "2026-11-20", "--tz", "UTC")
    assert result.returncode == 0
    assert result.stdout.strip().splitlines()[0] == "1795132800"


def test_cli_from_round_trip():
    to_out = run_cli("to", "1795132800", "--tz", "Asia/Kolkata")
    iso = to_out.stdout.strip().splitlines()[1]
    back = run_cli("from", iso)
    assert back.stdout.strip().splitlines()[0] == "1795132800"


def test_cli_diff():
    result = run_cli("diff", "1795132800", "1795219200", "--tz", "UTC")
    assert result.returncode == 0
    assert result.stdout.strip().splitlines() == ["86400", "1d"]


def test_cli_diff_dates():
    result = run_cli("diff", "2026-11-20", "2026-11-22", "--tz", "UTC")
    assert result.returncode == 0
    assert result.stdout.strip().splitlines() == ["172800", "2d"]


def test_cli_add():
    result = run_cli("add", "1795132800", "2d3h", "--tz", "UTC")
    assert result.returncode == 0
    lines = result.stdout.strip().splitlines()
    assert lines[0] == str(1795132800 + 2 * 86400 + 3 * 3600)
    assert lines[1] == "2026-11-22T03:00:00+00:00"


def test_cli_bad_tz():
    result = run_cli("to", "0", "--tz", "Nowhere/Special")
    assert result.returncode == 2
    assert "unknown timezone" in result.stderr


def test_cli_bad_input():
    result = run_cli("from", "not-a-date", "--tz", "UTC")
    assert result.returncode == 2
    assert "not a timestamp or ISO date" in result.stderr


def test_cli_no_args():
    result = run_cli()
    assert result.returncode == 2
