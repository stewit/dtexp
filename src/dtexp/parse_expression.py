"""Parse dtexp datetime expressions."""

import datetime
import re
from typing import Literal

from dtexp.addition import apply_addition_via_pendulum
from dtexp.conditions import handle_condition_expression
from dtexp.exceptions import DtexpParsingError
from dtexp.parse_timestamp import parse_timestamp_from_start

_BASIC_OPERATORS = {"-", "minus", "+", "plus", "/"}

_MINUS_OPERATORS = {"-", "minus"}

_PLUS_OPERATORS = {"+", "plus"}

_CONDITION_OPERATORS = {"next", "last", "upcoming", "previous"}


def parse_dtexp(
    expression: str,
    *,
    to_utc: bool = True,
    default_unaware_timezone: datetime.timezone = datetime.UTC,
    now: datetime.datetime | None = None,
    max_iso_timestamp_length: int = 35,
    fixed_iso_timestamp_length: int | None = None,
    max_iter: int = 1000,
    allow_conditions: bool = True,
) -> datetime.datetime:
    """Parse a dtexp datetime expression.

    Args:
    ----
        expression: The dtexp datetime expression, e.g. "now - 2w / w".
        to_utc: Whether the initial timestamp is immediately converted to utc.
            This happens before all operations are applied and leads to utc result.
        default_unaware_timezone: The timezone that is assumed for unaware absolute
            timestamps or now at the beginning of the expression.
        now: Allows to provide an explicit value for "now" that is used instead of invoking
            datetime.datetime.now(tzinfo=...).
        max_iso_timestamp_length: The beginning of the expression is scanned for iso timestamps.
            If you know that your source does e.g. not use microseconds, you can reduce this
            in order fail earlier for malformed expressions.
        fixed_iso_timestamp_length: If you know exactly how long isoformat timestamps
            at beginning of expression can be, you can set this to fail earlier on
            malformed expressions.
        max_iter: Evaluating conditions is iterative (brute force). This controls the maximum
            amount of iteration steps before failing.
        allow_conditions: May be set to False for expressions from untrusted sources,
            since evaluating conditions can have negative performance impacts.

    Returns:
    -------
        The parsed datetime object. Always timezone-aware.

    Raises:
    ------
        DtexpParsingError if parsing fails for any reason.

    """

    start, remaining = parse_timestamp_from_start(
        expression,
        to_utc=to_utc,
        now=now,
        max_iso_timestamp_length=max_iso_timestamp_length,
        fixed_iso_timestamp_length=fixed_iso_timestamp_length,
        default_unaware_timezone=default_unaware_timezone,
    )

    if start is None:
        raise DtexpParsingError("Could not parse a start datetime from beginning of expression")

    return parse_time_expression(
        split_result=split_expression(remaining),
        left=start,
        max_iter=max_iter,
        allow_conditions=allow_conditions,
    )


def parse_dtexp_interval(
    expression_left: str,
    expression_right: str,
    *,
    to_utc: bool = True,
    default_unaware_timezone: datetime.timezone = datetime.UTC,
    now: datetime.datetime | None = None,
    max_iso_timestamp_length: int = 35,
    fixed_iso_timestamp_length: int | None = None,
    max_iter: int = 1000,
    allow_conditions: bool = True,
) -> tuple[datetime.datetime, datetime.datetime]:
    """Parse two dtexp expressions with same parameters.

    Convenience wrapper for parse_dtexp for resolving intervals, i.e.
    two dtexp expressions.

    Returns the resolved dtexp expression results as a pair.
    """
    return (
        parse_dtexp(
            expression_left,
            to_utc=to_utc,
            default_unaware_timezone=default_unaware_timezone,
            now=now,
            max_iso_timestamp_length=max_iso_timestamp_length,
            fixed_iso_timestamp_length=fixed_iso_timestamp_length,
            max_iter=max_iter,
            allow_conditions=allow_conditions,
        ),
        parse_dtexp(
            expression_right,
            to_utc=to_utc,
            default_unaware_timezone=default_unaware_timezone,
            now=now,
            max_iso_timestamp_length=max_iso_timestamp_length,
            fixed_iso_timestamp_length=fixed_iso_timestamp_length,
            max_iter=max_iter,
            allow_conditions=allow_conditions,
        ),
    )


def parse_timedelta_for_pendulum_add(  # noqa: PLR0911
    timedelta_str: str, sign: Literal[1, -1] = 1
) -> dict[str, int]:
    """Parse timedelta into data for a pendulum add operation.

    Returns:
        dict of form {"days": -5} or {"months": 2} or similar that can be passed
        as kwargs into pendulum instance's .add method

    """

    try:
        match timedelta_str:
            case s if s.endswith("min"):
                return {"minutes": sign * int(s.removesuffix("min"))}
            case s if s.endswith("us"):
                return {"microseconds": sign * int(s.removesuffix("us"))}
            case s if s.endswith("w"):
                return {"weeks": sign * int(s.removesuffix("w"))}
            case s if s.endswith("d"):
                return {"days": sign * int(s.removesuffix("d"))}
            case s if s.endswith("m"):
                return {"months": sign * int(s.removesuffix("m"))}
            case s if s.endswith("h"):
                return {"hours": sign * int(s.removesuffix("h"))}
            case s if s.endswith("s"):
                return {"seconds": sign * int(s.removesuffix("s"))}
            case s if s.endswith("y"):
                return {"years": sign * int(s.removesuffix("y"))}
            case _:
                msg = f"Unknown timedelta str {timedelta_str}"
                raise DtexpParsingError(msg)
    except (ValueError, TypeError) as e:
        msg = f"Error parsing timedelta {timedelta_str}"
        raise DtexpParsingError(msg) from e


def extract_int_before_suffix(text: str, suffix: str, default_for_empty_num: int = 0) -> int:
    """Extract integer before suffix in a string.

    E.g for text "32d" with suffix "d" it returns 32.

    If nothing is present before the suffix, default_for_empty_num is returned.

    Raises DtexpParsingError if extracting fails.
    """
    num_str = text.removesuffix(suffix).strip()
    if num_str == "":
        return default_for_empty_num

    try:
        num = int(num_str)
    except (ValueError, TypeError) as e:
        msg = f"Could not parse integer at beginning of timedelta string: {text}"
        raise DtexpParsingError(msg) from e

    return num


def largest_fitting_multiple(current_val: int, num: int) -> int:
    """Compute largest multiple of num fitting into current_val.

    Actually this is the largest multiple of num fitting into
    current_val and for num=0 we return current_val instead.
    """
    return ((current_val // num) * num) if num != 0 else current_val


def apply_operator(  # noqa: C901, PLR0911
    left: datetime.datetime, operator: str, right: str
) -> datetime.datetime:
    """Apply operator to its operands."""
    if operator == "/":
        match right:
            case s if s.endswith("min"):
                return left.replace(
                    minute=largest_fitting_multiple(
                        left.minute, extract_int_before_suffix(s, "min")
                    ),
                    second=0,
                    microsecond=0,
                )
            case s if s.endswith("us"):
                return left.replace(
                    microsecond=largest_fitting_multiple(
                        left.microsecond, extract_int_before_suffix(s, "us")
                    ),
                )
            case s if s.endswith("d"):
                return left.replace(
                    day=largest_fitting_multiple(left.day, extract_int_before_suffix(s, "d")),
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            case s if s.endswith("m"):
                return left.replace(
                    month=largest_fitting_multiple(left.month, extract_int_before_suffix(s, "m")),
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            case s if s.endswith("y"):
                return left.replace(
                    year=largest_fitting_multiple(left.year, extract_int_before_suffix(s, "y")),
                    month=1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            case s if s.endswith("w"):
                week_in_year_number = left.isocalendar().week
                target_week_number = largest_fitting_multiple(
                    week_in_year_number, extract_int_before_suffix(s, "w")
                )
                return apply_addition_via_pendulum(
                    left, weeks=target_week_number - week_in_year_number, days=-1 * left.weekday()
                ).replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            case s if s.endswith("h"):
                return left.replace(
                    hour=largest_fitting_multiple(left.hour, extract_int_before_suffix(s, "h")),
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            case s if s.endswith("s"):
                return left.replace(
                    second=largest_fitting_multiple(left.second, extract_int_before_suffix(s, "s")),
                    microsecond=0,
                )
            case _:
                msg = f"Unknown period {right}"
                raise DtexpParsingError(msg)

    if operator in _MINUS_OPERATORS:
        return apply_addition_via_pendulum(left, **parse_timedelta_for_pendulum_add(right, -1))

    if operator in _PLUS_OPERATORS:
        return apply_addition_via_pendulum(left, **parse_timedelta_for_pendulum_add(right, +1))

    msg = f"Unknown operator {operator}"
    raise DtexpParsingError(msg)


_EXPRESSION_SPLIT_PATTERN = re.compile(
    r"([-+]|/|\bplus\b|\bminus\b|\bnext\b|\blast\b|\bupcoming\b|\bprevious\b|\bwhere\b|\bis\b|\band\b)"
)


def split_expression(expression_str: str) -> list[str]:
    """Split up expression string."""
    return [
        token.strip()
        for token in _EXPRESSION_SPLIT_PATTERN.split(
            expression_str,
        )
        if token.strip()
    ]


def parse_time_expression(
    split_result: list[str],
    left: datetime.datetime,
    *,
    max_iter: int = 1000,
    allow_conditions: bool = True,
) -> datetime.datetime:
    """Apply expression elements to a given left datetime.

    This is the main worker function that is applied recursively.
    """
    if len(split_result) == 0:
        return left

    first_element = split_result[0]

    if len(split_result) == 1:
        msg = f"Cannot understand expression with one operator and no arguments: {first_element}"
        raise DtexpParsingError(msg)

    # now only case len(split_result)>=2 left

    if first_element in _BASIC_OPERATORS:
        operator = first_element

        if len(split_result) == 2:
            return apply_operator(left, operator, split_result[1])  # ready!
        if len(split_result) == 3:
            msg = f"Missing value right of operator {split_result[2]}"
            raise DtexpParsingError(msg)

        return parse_time_expression(
            split_result[2:],
            left=apply_operator(left, operator, split_result[1]),
            max_iter=max_iter,
        )

    if first_element in _CONDITION_OPERATORS:
        if not allow_conditions:
            raise DtexpParsingError("Condition expressions are deactivated / not allowed.")

        result_date, remaining_elements = handle_condition_expression(
            split_result, left, max_iter=max_iter
        )

        if len(remaining_elements) == 0:
            return result_date

        return parse_time_expression(remaining_elements, left=result_date, max_iter=max_iter)

    msg = f"Unknown operator {first_element}"
    raise DtexpParsingError(msg)
