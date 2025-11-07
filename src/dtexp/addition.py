"""Handle addition to datetimes."""

import datetime

import pendulum


def apply_addition_via_pendulum(
    dt: datetime.datetime,
    years: int = 0,
    months: int = 0,
    weeks: int = 0,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
    microseconds: int = 0,
) -> datetime.datetime:
    """Use pendulum to add (or substract) from datetime intelligently.

    Using pendulum's add method provided human-expected results when
    adding or substracting e.g. months or years.
    """
    pendulum_result = pendulum.instance(dt).add(
        years=years,
        months=months,
        weeks=weeks,
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        microseconds=microseconds,
    )

    return datetime.datetime(
        pendulum_result.year,
        pendulum_result.month,
        pendulum_result.day,
        pendulum_result.hour,
        pendulum_result.minute,
        pendulum_result.second,
        pendulum_result.microsecond,
        tzinfo=dt.tzinfo,  # re-attach original timezone info
    )
