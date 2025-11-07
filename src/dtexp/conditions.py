"""Find a date in past/future fulfilling a condition."""

import calendar
import datetime
from typing import Literal

from dtexp.addition import apply_addition_via_pendulum
from dtexp.exceptions import DtexpMaxIterationError, DtexpParsingError

CONDITIONAL_DIRECTION_OPERATORS = {"next", "last", "upcoming", "previous"}


def weekday_occurrence_in_month_from_start(dt: datetime.datetime) -> int:
    """Return n where dt is the n'th occurrence of its weekday from month start.

    E.g. if its 2025-10-25 then this Saturday is the 4th occurence of this weekday
    in the month.
    """

    return ((dt.day - 1) // 7) + 1


def weekday_occurrence_in_month_from_end(dt: datetime.datetime) -> int:
    """Return n where dt is the n'th occurrence of its weekday from month end.

    E.g. if its 2025-10-25 then this Saturday is the 1st occurence of this weekday
    from the end of the month.
    """
    last_day = calendar.monthrange(dt.year, dt.month)[1]

    # Days remaining in month (including current day)
    days_from_end = last_day - dt.day

    return ((days_from_end - 1) // 7) + 1


def extract_condition_elements(elements: list[str]) -> tuple[list[str], list[str]]:
    """Get condition elements until a non-condition-element occurs.

    Returns pair of lists:
      * First contains the condition elements
      * second contains the remaining elements
    """
    condition_elements = []
    for element in elements:
        if element in {
            "+",
            "plus",
            "-",
            "minus",
            "/",
            "next",
            "past",
            "upcoming",
            "previous",
        }:
            break

        condition_elements.append(element)

    return condition_elements, elements[len(condition_elements) :]


def build_condition_dict(condition_elements: list[str]) -> dict[str, int]:
    """Gather conditions fromt the condition elements.

    Returns a dictionary of form {<time_unit>: number}, meaning that
    this time_unit's value of the datetime must equal the number.

    The entries of this dict later can be logically combined (e.g. with "and"),
    when evaluating the conditions.
    """
    if condition_elements[0] != "where":
        raise DtexpParsingError("Conditions must start with where")

    cond_dict_equals: dict[str, int] = {}
    remaining_condition_elements = condition_elements

    while len(remaining_condition_elements) > 0:
        if remaining_condition_elements[0] in {"where", "and"}:
            if len(remaining_condition_elements) < 4:
                msg = (
                    f"Condition expression must consist of 4 elements."
                    f" Got {remaining_condition_elements}"
                )
                raise DtexpParsingError(msg)

            condition_unit = remaining_condition_elements[1]
            if condition_unit not in {
                "us",
                "s",
                "min",
                "h",
                "d",
                "wd",
                "m",
                "y",
                "wdofms",
                "wdofme",
            }:
                msg = f"Cannot understand condition unit {condition_unit}"
                raise DtexpParsingError(msg)

            condition_type = remaining_condition_elements[2]
            if condition_type not in {"is"}:
                raise DtexpParsingError('Can only understand "is" conditions')

            condition_value = int(remaining_condition_elements[3])
            # Note: We do not check whether the condition_value fits to the condition_type
            # (i.e. weekdays only 0-6 etc., >0, ...). Instead, this will lead to just not
            # finding a result

            if cond_dict_equals.get(condition_unit) is None:
                cond_dict_equals[condition_unit] = condition_value
            elif cond_dict_equals[condition_unit] != condition_value:
                # We already have that condition
                msg = (
                    f"Cannot have two conditions for unit {condition_unit}"
                    " with two different values"
                    f" ({cond_dict_equals[condition_unit]}, {condition_value})"
                )
                raise DtexpParsingError(msg)

        remaining_condition_elements = remaining_condition_elements[4:]
    return cond_dict_equals


def eval_condition(dt: datetime.datetime, condition_elements: list[str]) -> bool:
    """Evaluate condition on datetime.

    Currently only accepts logical conjunction (and) of conditions.
    """

    cond_dict_equals = build_condition_dict(condition_elements)

    return (
        ((conv_val_days := cond_dict_equals.get("d")) is None or dt.day == conv_val_days)
        and ((conv_val_mins := cond_dict_equals.get("min")) is None or dt.minute == conv_val_mins)
        and ((conv_val_hours := cond_dict_equals.get("h")) is None or dt.hour == conv_val_hours)
        and (
            (conv_val_seconds := cond_dict_equals.get("s")) is None or dt.second == conv_val_seconds
        )
        and (
            (conv_val_weekday := cond_dict_equals.get("wd")) is None
            or dt.weekday() == conv_val_weekday
        )
        and (
            (conv_val_weekday_occurence_from_month_start := cond_dict_equals.get("wdofms")) is None
            or weekday_occurrence_in_month_from_start(dt)
            == conv_val_weekday_occurence_from_month_start
        )
        and (
            (conv_val_weekday_occurence_from_month_end := cond_dict_equals.get("wdofme")) is None
            or weekday_occurrence_in_month_from_end(dt) == conv_val_weekday_occurence_from_month_end
        )
        and ((conv_val_month := cond_dict_equals.get("m")) is None or dt.month == conv_val_month)
        and ((conv_val_year := cond_dict_equals.get("y")) is None or dt.year == conv_val_year)
    )


def find_date_by_condition(
    start_date: datetime.datetime,
    increment_direction: Literal[1, -1],
    start_increment: Literal[0, 1],
    target_unit: str,
    condition_elements: list[str],
    max_iter: int = 1000,
) -> datetime.datetime:
    """Find a date from a start date in one direction fulfilling a condition.

    Currently this simply iterates in the desired direction and checks the conditions
    at each step, i.e. brute force search.
    """

    iter_addition_params = {
        "microseconds": increment_direction if target_unit == "us" else 0,
        "seconds": increment_direction if target_unit == "s" else 0,
        "minutes": increment_direction if target_unit == "min" else 0,
        "hours": increment_direction if target_unit == "h" else 0,
        "days": increment_direction if target_unit in {"d", "wd"} else 0,
        "months": increment_direction if target_unit == "m" else 0,
        "years": increment_direction if target_unit == "y" else 0,
    }

    iteration_date = (
        start_date
        if start_increment == 0
        else apply_addition_via_pendulum(start_date, **iter_addition_params)
    )

    for _ in range(max_iter):
        if eval_condition(iteration_date, condition_elements):
            return iteration_date

        iteration_date = apply_addition_via_pendulum(iteration_date, **iter_addition_params)

    msg = f"Max condition iteration limit {max_iter} reached."
    raise DtexpMaxIterationError(msg)


def handle_condition_expression(
    split_result: list[str], left: datetime.datetime, max_iter: int = 1000
) -> tuple[datetime.datetime, list[str]]:
    """Handle condition expressions.

    Expects split_results to start with a condition expression.

    Will then resolve from left by iterating and checking the conditions up
    to max_iter steps.

    Returns a pair consisting of the resulting datetime and the list of remaining
    elements of split_result.
    """
    if len(split_result) < 2:
        raise DtexpParsingError("Condition expression too short")

    operator = split_result[0]

    if operator not in CONDITIONAL_DIRECTION_OPERATORS:
        msg = f"Condition expression must start with one of {CONDITIONAL_DIRECTION_OPERATORS}"
        raise DtexpParsingError(msg)

    increment_direction: Literal[-1, 1] = 1 if operator in {"next", "upcoming"} else -1
    start_increment: Literal[0, 1] = 0 if operator in {"next", "last"} else 1

    target_unit = split_result[1]

    if target_unit not in {"d", "wd", "w", "h", "min", "us", "s", "m", "y"}:
        msg = f"Unknown target unit {target_unit}."
        raise DtexpParsingError(msg)

    condition_elements, remaining_elements = extract_condition_elements(split_result[2:])

    result_date = find_date_by_condition(
        start_date=left,
        increment_direction=increment_direction,
        start_increment=start_increment,
        target_unit=target_unit,
        condition_elements=condition_elements,
        max_iter=max_iter,
    )

    return result_date, remaining_elements
