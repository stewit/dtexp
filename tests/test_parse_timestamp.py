import datetime

import pytest

from dtexp.exceptions import DtexpParsingError
from dtexp.parse_timestamp import parse_timestamp, parse_timestamp_from_start


def test_parse_timestamp_from_start():
    # full length timestamp
    result, remaining = parse_timestamp_from_start("2025-06-04T09:42:24.000001+00:00")
    assert result.year == 2025
    assert result.day == 4
    assert result.hour == 9

    assert result.utcoffset().total_seconds() == 0.0
    assert remaining == ""

    # full length timestamp with additional remaining text
    result, remaining = parse_timestamp_from_start("2025-06-04T09:42:24.000001+00:00a")
    assert result.year == 2025
    assert result.day == 4
    assert result.hour == 9

    assert result.utcoffset().total_seconds() == 0.0
    assert remaining == "a"

    # now
    near_now = datetime.datetime.now(tz=datetime.UTC)
    result, remaining = parse_timestamp_from_start("now")

    assert abs((result - near_now).total_seconds()) < 10.0

    assert result.utcoffset().total_seconds() == 0.0
    assert remaining == ""

    # now with remaining text
    near_now = datetime.datetime.now(tz=datetime.UTC)
    result, remaining = parse_timestamp_from_start("nowa")

    assert abs((result - near_now).total_seconds()) < 10.0

    assert result.utcoffset().total_seconds() == 0.0
    assert remaining == "a"

    # now with explicit now timestamp
    now_dt = datetime.datetime(year=2025, month=6, day=5, tzinfo=datetime.UTC)
    result, remaining = parse_timestamp_from_start(
        "now",
        now=now_dt,
    )

    assert result == now_dt
    assert result.utcoffset().total_seconds() == 0.0
    assert remaining == ""

    # timestamp without timezone, should always be interpreted as utc!
    result, remaining = parse_timestamp_from_start("2025-06-04T09:42:24")
    assert result.year == 2025
    assert result.day == 4
    assert result.hour == 9

    assert result.utcoffset().total_seconds() == 0.0
    assert remaining == ""

    # timestamp with explicit different timezone and no utc conversion
    result, remaining = parse_timestamp_from_start("2025-06-04T09:42:24+02:00", to_utc=False)
    assert result.year == 2025
    assert result.day == 4
    assert result.hour == 9  # not changed since to_utc was False

    assert result.utcoffset().total_seconds() == 7200.0  # offset since to_utc was false
    assert remaining == ""

    # timestamp with explicit different timezone and utc conversion
    result, remaining = parse_timestamp_from_start("2025-06-04T09:42:24+02:00")
    assert result.year == 2025
    assert result.day == 4
    assert result.hour == 7  # changed since utc conversion is True by default

    assert result.utcoffset().total_seconds() == 0.0  # utc conversion happened
    assert remaining == ""

    # gibberish
    result, remaining = parse_timestamp_from_start(
        "blahhh",
    )
    assert result is None
    assert remaining == "blahhh"


def test_parse_timestamp():
    # full length timestamp
    result = parse_timestamp("2025-06-04T09:42:24.000001+00:00")
    assert result.year == 2025
    assert result.day == 4
    assert result.hour == 9

    assert result.utcoffset().total_seconds() == 0.0

    # too long / extra content
    with pytest.raises(DtexpParsingError):
        result = parse_timestamp("2025-06-04T09:42:24.000001+00:00a")

    # gibberish
    with pytest.raises(DtexpParsingError):
        result = parse_timestamp("blahhh")


def test_timezone_handling_for_absolute_start():
    result = parse_timestamp("2025-06-04T09:42:24.000001+00:00")
    assert result.tzinfo == datetime.UTC
    assert result.hour == 9

    result = parse_timestamp("2025-06-04T09:42:24.000001+01:00")
    assert result.tzinfo == datetime.UTC
    assert result.hour == 8

    result = parse_timestamp("2025-06-04T09:42:24.000001+01:00", to_utc=False)
    assert result.tzinfo == datetime.timezone(datetime.timedelta(hours=1))
    assert result.hour == 9

    result = parse_timestamp(
        "2025-06-04T09:42:24.000001",
        default_unaware_timezone=datetime.timezone(datetime.timedelta(hours=2)),
    )
    assert result.tzinfo == datetime.UTC
    assert result.hour == 7

    result = parse_timestamp(
        "2025-06-04T09:42:24.000001",
        default_unaware_timezone=datetime.timezone(datetime.timedelta(hours=2)),
        to_utc=False,
    )
    assert result.tzinfo == datetime.timezone(datetime.timedelta(hours=2))
    assert result.hour == 9


def test_timezone_handling_for_now_start():
    near_now = datetime.datetime.now(tz=datetime.UTC)
    result = parse_timestamp("now")
    assert result.tzinfo == datetime.UTC
    assert result - near_now < datetime.timedelta(seconds=5)

    near_now = datetime.datetime.now(tz=datetime.UTC)
    result = parse_timestamp("now", to_utc=False)
    assert result.tzinfo == datetime.UTC
    assert result - near_now < datetime.timedelta(seconds=5)

    near_now = datetime.datetime.now(tz=datetime.UTC)
    result = parse_timestamp(
        "now", default_unaware_timezone=datetime.timezone(datetime.timedelta(hours=3))
    )
    assert result.tzinfo == datetime.UTC
    assert result - near_now < datetime.timedelta(seconds=5)

    near_now = datetime.datetime.now(tz=datetime.UTC)
    result = parse_timestamp(
        "now",
        default_unaware_timezone=datetime.timezone(datetime.timedelta(hours=3)),
        to_utc=False,
    )
    assert result.tzinfo == datetime.timezone(datetime.timedelta(hours=3))
    assert result.hour != near_now.hour
    assert result - near_now < datetime.timedelta(seconds=5)


def test_timezone_handling_for_now_start_with_explicit_now_value():
    explicit_aware_now_utc = datetime.datetime(
        year=2025,
        month=6,
        day=5,
        hour=12,
        minute=0,
        second=0,
        tzinfo=datetime.UTC,
    )

    result = parse_timestamp("now", now=explicit_aware_now_utc)
    assert result == explicit_aware_now_utc
    assert result.tzinfo == datetime.UTC

    explicit_aware_now_non_utc = datetime.datetime(
        year=2025,
        month=6,
        day=5,
        hour=12,
        minute=0,
        second=0,
        tzinfo=datetime.timezone(datetime.timedelta(hours=5)),
    )
    result = parse_timestamp("now", now=explicit_aware_now_non_utc)
    assert result.hour == 7  # converted to utc
    assert result.tzinfo == datetime.UTC

    result = parse_timestamp("now", now=explicit_aware_now_non_utc, to_utc=False)
    assert result.hour == 12  # kept timezone
    assert result.tzinfo == datetime.timezone(datetime.timedelta(hours=5))

    explicit_unaware_now = datetime.datetime(  # noqa: DTZ001
        year=2025,
        month=6,
        day=5,
        hour=12,
        minute=0,
        second=0,
    )
    result = parse_timestamp("now", now=explicit_unaware_now)
    assert result == explicit_aware_now_utc  # it is interpreted as having utc
    assert result.tzinfo == datetime.UTC

    result = parse_timestamp(
        "now",
        now=explicit_unaware_now,
        default_unaware_timezone=datetime.timezone(datetime.timedelta(hours=5)),
    )
    assert result.hour == 7  # it is converted to utc
    assert result.tzinfo == datetime.UTC

    result = parse_timestamp(
        "now",
        now=explicit_unaware_now,
        default_unaware_timezone=datetime.timezone(datetime.timedelta(hours=5)),
        to_utc=False,
    )
    assert result.hour == 12  # kept timezone
    assert result.tzinfo == datetime.timezone(datetime.timedelta(hours=5))

    with pytest.raises(DtexpParsingError):
        parse_timestamp("now_", now=explicit_aware_now_non_utc)
