"""Parsing timestamps or now at beginning of expressions."""

import datetime

from dtexp.exceptions import DtexpParsingError


def check_aware(dt: datetime.datetime) -> bool:
    """Check whether Python datetime is non-naive."""
    # see https://stackoverflow.com/a/27596917
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def ensure_aware(
    dt: datetime.datetime,
    default_unaware_timezone: datetime.timezone = datetime.UTC,
) -> datetime.datetime:
    """Ensure that a datetime is aware, applying default_unaware_timezone to unaware datetimes.

    Return aware datetimes as is. For unaware datetimes this sets the timezone
    to default_unaware_timezone.

    The result is always aware.
    """
    if not check_aware(dt):
        return dt.replace(tzinfo=default_unaware_timezone)
    return dt


def parse_isoformat_from_start(
    text: str,
    max_iso_timestamp_length: int = 35,
    # max length example: "2025-01-01T00:00:00.000000000+00:00"
    fixed_iso_timestamp_length: int | None = None,
) -> tuple[datetime.datetime | None, str]:
    """Parse isoformat from start of a string.

    The requirements here are
    * parse isoformat from beginning of strings without clearly defined
      separation character between timestamp and the remaining string
    * stay compatible with what Python's datetime.fromisoformat(...) is
      and is able and will be able to parse in the future

    The later disallows using a regexp here. Therefore we pursue the following
    strategy:

    * start at a maximal possible isoformat timestamp length
    * try to parse, decreasing possible length, until it succeeds or
    reaches zero characters.

    This could possibly be optimized at several points. However the requirements
    specified above must be taken into account!

    Returns a pair of shape
        parsed timestamp (or None if no timestamp found), remaining text
    """

    if not text or not text.strip():
        return None, text

    text = text.strip()

    # Fall back to trying all lengths from highest to lowest
    for i in (
        range(min(len(text), max_iso_timestamp_length), 1, -1)
        if fixed_iso_timestamp_length is None
        else (fixed_iso_timestamp_length,)
    ):
        candidate = text[:i]
        try:
            dt = datetime.datetime.fromisoformat(candidate)

        except ValueError:
            continue
        else:
            remaining = text[i:]
            return dt, remaining

    return None, text


def parse_timestamp_from_start(
    text: str,
    *,
    to_utc: bool = True,
    now: datetime.datetime | None = None,
    max_iso_timestamp_length: int = 35,
    fixed_iso_timestamp_length: int | None = None,
    default_unaware_timezone: datetime.timezone = datetime.UTC,
) -> tuple[datetime.datetime | None, str]:
    """Parse datetime from start of string.

    Can handle now or isoformat strings at the beginning.

    Returns pair
        (datetime, remaining_string)
    on success and
        (None, text)
    if no datetime could be extracted from start of text.

    Important: Makes sure that the resulting datetime is timezone aware and by default
    even that it has UTC timezone.
    * If no timezone is specified (unaware) it will be interpreted as default_unaware_timezone
      (defaulting to utc)
    * if to_utc is True (the default) the datetime will be converted to utc timezone.
      Set to_utc to False to keep other timezones.

    Furthermore this evaluates "now" at runtime. You can supply a datetime object
    using the parameter now to enforce now to be this datetime.

    "now" will yield a datetime with timezone default_unaware_timezone if to_utc is False.
    """
    datetime_obj: datetime.datetime | None
    if text.lower().startswith("now"):
        datetime_obj = datetime.datetime.now(tz=default_unaware_timezone) if now is None else now
        remaining = text[3:]
    else:
        datetime_obj, remaining = parse_isoformat_from_start(
            text,
            max_iso_timestamp_length=max_iso_timestamp_length,
            fixed_iso_timestamp_length=fixed_iso_timestamp_length,
        )

    if datetime_obj is None:
        return None, remaining

    datetime_obj = ensure_aware(datetime_obj, default_unaware_timezone=default_unaware_timezone)

    if to_utc:
        datetime_obj = datetime_obj.astimezone(datetime.UTC)

    return datetime_obj, remaining


def parse_timestamp(
    timestamp: str,
    *,
    to_utc: bool = True,
    now: datetime.datetime | None = None,
    default_unaware_timezone: datetime.timezone = datetime.UTC,
) -> datetime.datetime:
    """Parse a datetime from "now" or an isoformat timestamp string.

    Expects only now or the timestamp to be contained and no remaining characters.

    to_utc, now, and default_unaware_timezone are handled as described for
    parse_timestamp_from_start.

    Raises DtexpParsingError if either no parsing succeeded from beginning of timestamp
    or unparsed characters remain.

    Returns parsed datetime object.
    """
    result, remaining = parse_timestamp_from_start(
        timestamp,
        to_utc=to_utc,
        now=now,
        fixed_iso_timestamp_length=len(timestamp),
        default_unaware_timezone=default_unaware_timezone,
    )

    if result is None:
        raise DtexpParsingError("Could not parse timestamp")

    if len(remaining) > 0:
        raise DtexpParsingError(
            "Only beginning could be parsed as timestamp, found remaining characters."
        )

    return result
