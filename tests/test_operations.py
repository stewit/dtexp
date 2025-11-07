import datetime

import pytest

from dtexp import DtexpParsingError, parse_dtexp, parse_dtexp_interval
from dtexp.parse_expression import apply_operator


@pytest.fixture
def explicit_aware_now_utc():
    return datetime.datetime(
        year=2025,
        month=6,
        day=5,
        hour=12,
        minute=0,
        second=0,
        tzinfo=datetime.UTC,
    )


def test_basic_examples(explicit_aware_now_utc):  # noqa: PLR0915
    result = parse_dtexp("now", now=explicit_aware_now_utc)
    assert result == explicit_aware_now_utc

    result = parse_dtexp("now - 2d", now=explicit_aware_now_utc)
    assert result == explicit_aware_now_utc.replace(day=3)

    result = parse_dtexp("2025-06-03T13:51:24.354+00:00 / h")
    assert result.isoformat() == "2025-06-03T13:00:00+00:00"

    result = parse_dtexp("now / m + 8h + 15min", now=explicit_aware_now_utc)
    assert result.isoformat() == "2025-06-01T08:15:00+00:00"

    result = parse_dtexp("now / 5min - 5min", now=explicit_aware_now_utc)
    assert result.isoformat() == "2025-06-05T11:55:00+00:00"

    result = parse_dtexp("now / 5min - 5min", now=explicit_aware_now_utc.replace(minute=2))
    assert result.isoformat() == "2025-06-05T11:55:00+00:00"

    result = parse_dtexp("now / 5min - 5min", now=explicit_aware_now_utc.replace(minute=6))
    assert result.isoformat() == "2025-06-05T12:00:00+00:00"

    result = parse_dtexp("now - 2h", now=explicit_aware_now_utc)
    assert result.isoformat() == "2025-06-05T10:00:00+00:00"

    result = parse_dtexp("now / 15min - 15min", now=explicit_aware_now_utc)
    assert result.isoformat() == "2025-06-05T11:45:00+00:00"

    result = parse_dtexp("now / 15min - 15min", now=explicit_aware_now_utc.replace(minute=2))
    assert result.isoformat() == "2025-06-05T11:45:00+00:00"

    result = parse_dtexp("now / 15min", now=explicit_aware_now_utc)
    assert result.isoformat() == "2025-06-05T12:00:00+00:00"

    result = parse_dtexp("now / 15min", now=explicit_aware_now_utc.replace(minute=2))
    assert result.isoformat() == "2025-06-05T12:00:00+00:00"

    result = parse_dtexp("now / 15min + 15min", now=explicit_aware_now_utc)
    assert result.isoformat() == "2025-06-05T12:15:00+00:00"

    result = parse_dtexp("now / 15min + 15min", now=explicit_aware_now_utc.replace(minute=2))
    assert result.isoformat() == "2025-06-05T12:15:00+00:00"

    # month difference around differently length months
    result = parse_dtexp("2025-03-30T02:00:00Z - 1m")
    assert result.isoformat() == "2025-02-28T02:00:00+00:00"

    # chained
    result = parse_dtexp("2025-03-30T15:42:00Z - 1m + 2d / h")
    assert result.isoformat() == "2025-03-02T15:00:00+00:00"

    result = parse_dtexp("2025-03-30T15:42:00Z")  # step 1
    assert result.isoformat() == "2025-03-30T15:42:00+00:00"

    result = parse_dtexp("2025-03-30T15:42:00Z - 1m")  # step 2
    assert result.isoformat() == "2025-02-28T15:42:00+00:00"

    result = parse_dtexp("2025-03-30T15:42:00Z - 1m + 2d")  # step 3
    assert result.isoformat() == "2025-03-02T15:42:00+00:00"

    # / operator
    result = parse_dtexp("2025-03-30T15:42:00Z / d")
    assert result.isoformat() == "2025-03-30T00:00:00+00:00"

    result = parse_dtexp("2025-03-30T15:42:00Z / 15min")
    assert result.isoformat() == "2025-03-30T15:30:00+00:00"

    result = parse_dtexp("2025-03-30T15:42:00Z / 2h")
    assert result.isoformat() == "2025-03-30T14:00:00+00:00"

    # conditions
    result = parse_dtexp("2025-03-30T15:42:00Z next d where m is 7 and d is 4")
    assert result.isoformat() == "2025-07-04T15:42:00+00:00"

    result = parse_dtexp("2025-03-30T15:42:00Z last d where wd is 1")
    assert result.isoformat() == "2025-03-25T15:42:00+00:00"

    result = parse_dtexp("2025-03-30T15:42:00Z next d where wd is 6")
    assert result.isoformat() == "2025-03-30T15:42:00+00:00"

    # starting date is already sunday
    result = parse_dtexp("2025-03-30T15:42:00Z upcoming d where wd is 6")
    assert result.isoformat() == "2025-04-06T15:42:00+00:00"

    # starting date is already sunday
    result = parse_dtexp("2025-03-30T15:42:00Z previous d where wd is 6")
    assert result.isoformat() == "2025-03-23T15:42:00+00:00"

    # Next first Sunday in September
    result = parse_dtexp("2024-09-18T12:27:31Z next d where m is 9 and wd is 6 and wdofms is 1 / d")
    assert result.isoformat() == "2025-09-07T00:00:00+00:00"

    # Next last Sunday in September
    result = parse_dtexp("2024-09-18T12:27:31Z next d where m is 9 and wd is 6 and wdofme is 1 / d")
    assert result.isoformat() == "2024-09-29T00:00:00+00:00"

    result = parse_dtexp("2024-09-18T12:27:31Z + 1w")
    assert result.isoformat() == "2024-09-25T12:27:31+00:00"

    result = parse_dtexp("2024-09-18T12:27:31Z + 1s")
    assert result.isoformat() == "2024-09-18T12:27:32+00:00"

    result = parse_dtexp("2024-09-18T12:27:31Z + 1us")
    assert result.isoformat() == "2024-09-18T12:27:31.000001+00:00"

    result = parse_dtexp("2024-09-18T12:27:31Z + 1y")
    assert result.isoformat() == "2025-09-18T12:27:31+00:00"

    result = parse_dtexp("2024-09-18T12:27:31Z / y")
    assert result.isoformat() == "2024-01-01T00:00:00+00:00"

    result = parse_dtexp("2024-09-18T12:27:31Z / w")
    assert result.isoformat() == "2024-09-16T00:00:00+00:00"

    result = parse_dtexp("2024-09-18T12:27:31Z / 5s")
    assert result.isoformat() == "2024-09-18T12:27:30+00:00"

    result = parse_dtexp("2024-09-18T12:27:31.000007Z / 5us")
    assert result.isoformat() == "2024-09-18T12:27:31.000005+00:00"

    result = parse_dtexp("2025-11-03T12:27:31.000007Z / 7w")
    assert result.isoformat() == "2025-10-13T00:00:00+00:00"

    result = parse_dtexp("2025-11-04T12:27:31.000007Z / 7w")
    assert result.isoformat() == "2025-10-13T00:00:00+00:00"

    result = parse_dtexp("2025-11-03T12:27:31.000007Z / w")
    assert result.isoformat() == "2025-11-03T00:00:00+00:00"

    result = parse_dtexp("2025-11-04T12:27:31.000007Z / w")
    assert result.isoformat() == "2025-11-03T00:00:00+00:00"

    result = parse_dtexp("2025-11-04T12:27:31.000007Z / 1w")
    assert result.isoformat() == "2025-11-03T00:00:00+00:00"

    left, right = parse_dtexp_interval(
        "2025-11-04T12:27:31Z / 10min - 10min", "2025-11-04T12:27:31Z / 10min"
    )
    assert left.isoformat() == "2025-11-04T12:10:00+00:00"
    assert right.isoformat() == "2025-11-04T12:20:00+00:00"


def test_basic_exceptions():
    with pytest.raises(DtexpParsingError):
        parse_dtexp("")

    with pytest.raises(DtexpParsingError):
        parse_dtexp("-------")

    with pytest.raises(DtexpParsingError):
        parse_dtexp("now - +")

    with pytest.raises(DtexpParsingError):
        parse_dtexp("now - 2")

    with pytest.raises(DtexpParsingError):
        parse_dtexp("now - min")

    with pytest.raises(DtexpParsingError):
        parse_dtexp("now - 2hh")

    with pytest.raises(DtexpParsingError):
        parse_dtexp("now - a2h")

    with pytest.raises(DtexpParsingError):
        parse_dtexp("now / a2h")

    with pytest.raises(DtexpParsingError):
        parse_dtexp("2024-09-18T12:27:31.000007Z / fffff")

    with pytest.raises(DtexpParsingError):
        parse_dtexp("2024-09-18T12:27:31.000007Z k fffff")

    with pytest.raises(DtexpParsingError):
        apply_operator(datetime.datetime.now(), "kkkkk", "42min")  # noqa: DTZ005

    with pytest.raises(DtexpParsingError):
        parse_dtexp("2024-09-18T12:27:31.000007Z + 2 +")

    with pytest.raises(DtexpParsingError):
        parse_dtexp("2024-09-18T12:27:31.000007Z next d where d is 4", allow_conditions=False)
    with pytest.raises(DtexpParsingError):
        parse_dtexp("2024-09-18T12:27:31.000007Z unknown d where d is 4", allow_conditions=False)
