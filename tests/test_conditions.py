import datetime

import pytest

from dtexp import DtexpParsingError
from dtexp.conditions import (
    eval_condition,
    find_date_by_condition,
    handle_condition_expression,
)
from dtexp.exceptions import DtexpMaxIterationError


def test_eval_condition_errors():
    with pytest.raises(DtexpParsingError):
        eval_condition(datetime.datetime.now(tz=datetime.UTC), ["wrong", "d", "is", "25"])

    with pytest.raises(DtexpParsingError):
        eval_condition(
            datetime.datetime.now(tz=datetime.UTC),
            ["where", "d", "is", "25", "and"],
        )

    with pytest.raises(DtexpParsingError):
        eval_condition(
            datetime.datetime.now(tz=datetime.UTC),
            ["where", "unknown", "is", "25", "and"],
        )

    with pytest.raises(DtexpParsingError):
        eval_condition(
            datetime.datetime.now(tz=datetime.UTC),
            ["where", "d", "UNKNOWN", "25", "and"],
        )

    with pytest.raises(DtexpParsingError):
        eval_condition(
            datetime.datetime.now(tz=datetime.UTC),
            ["where", "d", "is", "25", "and", "d", "is", "30"],
        )

    with pytest.raises(DtexpMaxIterationError):
        find_date_by_condition(
            datetime.datetime.now(tz=datetime.UTC),
            1,
            0,
            "d",
            ["where", "y", "is", "1970"],
        )

    with pytest.raises(DtexpParsingError):
        handle_condition_expression(["next"], left=datetime.datetime.now(tz=datetime.UTC))

    with pytest.raises(DtexpParsingError):
        handle_condition_expression(
            ["UNKNOWN_op", "d", "where", "d", "is", "25"],
            left=datetime.datetime.now(tz=datetime.UTC),
        )

    with pytest.raises(DtexpParsingError):
        handle_condition_expression(
            ["next", "UNKNOWN", "where", "d", "is", "25"],
            left=datetime.datetime.now(tz=datetime.UTC),
        )
