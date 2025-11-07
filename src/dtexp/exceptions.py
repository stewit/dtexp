"""dtexp exception classes."""


class DtexpParsingError(ValueError):
    """Error parsing an expression with dtexp."""


class DtexpMaxIterationError(DtexpParsingError):
    """Maximum iterations reached for condition evaluation."""
