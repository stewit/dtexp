![Coverage](https://raw.githubusercontent.com/stewit/dtexp/badges/coverage-badge.svg)

# dtexp
**dtexp** is a Python datetime expression parsing library.

## Introduction
**dtexp** parses datetime expressions relative to a start date like
* `now` => current datetime (utc by default)
* `now - 2d` => Go back two days from now
* `2025-06-03T13:51:24.354+00:00 / h` => start of hour, i.e. 2025-06-03T13:00:00.000+00:00
* `now / m + 8h + 15min` => 08:15 at 1st day of current month
* `now / 5min - 5min` => start of last fully completed 5min interval.

Expressions are parsed into Python builtin timezone-aware `datetime.datetime` objects.

**dtexp** parses its own unambigous / explicit datetime expression syntax as demonstrated in the examples above. It is not a "fuzzy" parser for human readable dates like [dateparser](https://dateparser.readthedocs.io/en/latest/).

E.g. **dtexp** enables readable but explicit specifications for timeseries data intervals like
* "last two hours": `now - 2h` to `now`
* "give/show me the last fully-completed 15min time interval aligned to hour of my data before now": `now / 15min - 15min` to `now / 15 min`
* "give/show me the current 15min interval aligned to hour I am in": `now / 15min` to `now / 15min + 15min`


## Usage

### Installation

```shell
pip install dtexp
```

or using `uv`:

```
uv add dtexp
```

Note: dtexp has [pendulum](https://pendulum.eustace.io/) as single dependency.

### Basic usage
```python
from dtexp import parse_dtexp

parse_dtexp("now - 2d") # results in datetime object with utc timezone.
```

The basic time units are `us` (microsecond), `s` (second), `min` (minute), `h` (hour), `d` (day), `w` (week), `m` (month!) and `y` (year). Additionally, for conditions, `wd` (weekday, from 0=Monday to 6=Sunday) and `wdofms` (weekday occurence from month start) and `wdofme` (weekday occurence from month end) are allowed.

Note: **dtexp** uses [pendulum](https://pendulum.eustace.io/) for calculating meaningful timedeltas and applying them intelligently, e.g.

```python
parse_dtexp("2025-03-30T02:00:00Z - 1m") # results in 2025-02-28 02:00:00+00:00
```
However, **dtexp** always returns a Python builtin datetime.datetime object.

### Chaining operations
Operations can be chained. Example:

```python
parse_dtexp("2025-03-30T15:42:00Z - 1m + 2d / h") # results in 2025-03-02 15:00:00+00:00
```
The steps in this example are:
* start at `2025-03-30T15:42:00Z`
* substract 1 month (resulting in `2025-02-28 15:42:00+00:00`)
* add two days (`2025-03-02 15:42:00+00:00`)
* goto start of current hour (`2025-03-02 15:00:00+00:00`)

Operations are simply processed from left to right. There are no precedences and you cannot use parentheses.

### The `/` operator

The `/` operator goes to the start of a time interval defined by the right operand. Time intervals are aligned to the next higher time unit (day intervals are aligned to the month). Examples:

```python
parse_dtexp("2025-03-30T15:42:00Z / d")
# => start of current day: 2025-03-30 00:00:00+00:00

parse_dtexp("2025-03-30T15:42:00Z / 15min")
# => start of current 15min interval: 2025-03-30 15:30:00+00:00

parse_dtexp("2025-03-30T15:42:00Z / 2h")
# => start of current 2h interval: 2025-03-30 14:00:00+00:00
```

Think of the intervals subdividing the next higher time unit (non-overlapping), always starting from 0 for the interval's and smaller time units. (Note: weeks are aligned to week number in year).

The `/` operator enables specification of intervals relative from a given timestamp, like *"last fully-complete 10min interval before now"*,  which is quite practical when working with timeseries data:

```python
# Generate some timeseries data
import pandas as pd
import numpy as np
timestamps = pd.date_range(
    freq="2min", start="2025-10-30T00:00:00Z", end="2025-11-01T00:00:00Z"
)
s = pd.Series(
        np.random.randn(len(timestamps)),
        index=pd.date_range(
            freq="2min", start="2025-10-30T00:00:00Z", end="2025-11-01T00:00:00Z"
        )
)

# We want to use the same reference value for "now" for both start and end of the interval
#     current_dt = datetime.datetime.now(datetime.UTC)
current_dt = datetime.datetime(
    year=2025, month=10, day=30,
    hour=12, minute=14, second=45,
    tzinfo=datetime.UTC
) # to get reproducible example we explicitely set the datetime object!

# Extract the last complete 10 minute interval before the current timestamp
start = parse_dtexp("now / 10min - 10min", now=current_dt)
end = parse_dtexp("now / 10min", now=current_dt)

s[start:end]
# results in:
# 2025-10-30 12:00:00+00:00    0.220729
# 2025-10-30 12:02:00+00:00    0.218195
# 2025-10-30 12:04:00+00:00    1.248827
# 2025-10-30 12:06:00+00:00    0.455321
# 2025-10-30 12:08:00+00:00   -0.945959
# 2025-10-30 12:10:00+00:00    1.083654
```

### Conditions (experimental)

You can find a timestamp in the past or future form a given timestamp that fulfills a condition. Examples:

```python
parse_dtexp("2025-03-30T15:42:00Z next d where m is 7 and d is 4")
# => next july the forth: 2025-07-04 15:42:00+00:00

# weekday (wd) 1 corresponds to Tuesday
parse_dtexp("2025-03-30T15:42:00Z last d where wd is 1")
# => last Tuesday: 2025-03-25 15:42:00+00:00

parse_dtexp("2025-03-30T15:42:00Z next d where wd is 6")
# => next Sunday: 2025-03-30 15:42:00+00:00
# (the starting date was already a Sunday!)

parse_dtexp("2025-03-30T15:42:00Z upcoming d where wd is 6")
# => upcoming Sunday: 2025-04-06 15:42:00+00:00
# (upcoming does not allow the same as start)

parse_dtexp("2025-03-30T15:42:00Z previous d where wd is 6")
# => previous Sunday: 2025-03-23 15:42:00+00:00
# (previous does not allow the same as start)

# Next first Sunday in September
parse_dtexp("2024-09-18T12:27:31Z next d where m is 9 and wd is 6 and wdofms is 1 / d")
# => 2025-09-07 00:00:00+00:00
# (wdofms means: weekday occurence from month start)
```

Notes on conditions:
* conditions can be chained with other operators.
* conditions can only be linked with `and`


### Timezone handling

**dtexp** guarantees timezone aware results in a controllable way.

#### Step 1: Ensuring aware start datetime object
Unaware absolute timestamps at the beginning of expressions are interpreted to be aware using the `default_unaware_timezone` parameter value of the `parse_dtexp` function, which itself defaults to `datetime.UTC`. Aware absolute timestamps are simply parsed into an aware datetime object.

Similarly, `now` is computed as an aware object using `default_unaware_timezone`. If the `now` parameter to parse is provided instead as a datetime object,
* it is taken as it is as start datetime object if it is aware
* it is interpreted as aware using `default_unaware_timezone` if it is unaware.

Now we have an aware start datetime object.

#### Step 2: possibly convert to utc before proceeding.
The extracted start datetime object is then immediately converted to utc, if `to_utc` is `True`, which it is by default. If `to_utc`is False, it is used as is for all following computations

From this moment onwards, the timezone is fixed.

#### Step 3: Evaluation operators and result
All subsequent operations are excuted on datetime objects with this timezone and the overall result at the end has this timezone.

### hints and tips
* You may use `minus` and `plus` instead of `-` and `+`. This allows e.g. to provide expressions in query parameters in urls like `start=now&end=now plus 2d` (or, properly url encoded `start=now&end=now+plus+2d`) which are still easily readable.
* The `parse_dtexp` function comes with a boolean parameter `allow_conditions` that is `True` by default. Setting it to False will disable condition expressions, which may be necessary to avoid difficult-to-calculate and potentially excessive parsing times due to the current naive iterative evaluation / processing of conditional expressions. Consider setting it to False for externally provided expressions, in particular if you parse a lot of them. Another possibility to control parsing time in this case is to use the `max_iter` parameter (default 1000) to set a limit for evaluation steps of a single condition part in the expression.
* There is a convenience function `parse_dtexp_interval` that expects two expressions as argument and the same keyword arguments as `parse_dtexp`. It parses both expressions using the same settings and returns the corresponding pair of result datetime objects.

## Development

Test an expression from command line:
```shell
uv run python -c 'from dtexp import parse_dtexp; print(parse_dtexp("now - 5d"))'
```

Run tests with locked Python version:
```shell
./run test
```

Run tests for all supported Python versions:
```shell
./run test-py-versions
```

Formatting:
```shell
./run format
```

Linting:
```shell
./run lint
```

Typechecking:
```shell
./run typecheck
```

Run all checks, similar to CI:
```shell
./run check
```


### Build
Build wheel via
```
rm -r dist && uv build
```

Results will appear in `dist` subdirectory

### Release

#### Preparations
All in develop branch:
* `uv lock --upgrade` to upgrade dependencies.
* Change `__version__` in main `__init__.py`.
* Change `version` in `pyproject.toml`.
* Add CHANGELOG.md entry
* Check that `classifiers` in `pyproject.toml` includes all Python versions.
* Check that `run` script `test-py-versions` command includes all Python versions. 
* Run all checks `./run check`.
* Check build runs via `rm -r dist && uv build`.

#### Actual release
Run from develop branch:

```shell
./release.sh 0.1.0      # replace with actual version
```

This will check some things, manage branch, tag, build and publish.
