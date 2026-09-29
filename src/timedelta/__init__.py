# Copyright (c) 2026 Stig B. Dørmænen
"""A minimal CLI for computing the time delta between two points in time."""

import calendar
import re
from contextlib import suppress
from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import click

_DATE_PRECISION_RANK = {"date": 0, "hours": 1, "minutes": 2, "seconds": 3}

_DATE_PRECISION_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[T ](?P<hh>\d{2})(?::(?P<mm>\d{2})(?::(?P<ss>\d{2}))?)?)?",
)


def _looks_like_zone_name(token: str) -> bool:
    """Return True if token looks like an IANA timezone name (e.g. Europe/Oslo)."""
    return token in ("UTC", "GMT") or "/" in token


def _input_date_precision(value: str) -> str | None:
    """Return the granularity of a date/time input.

    One of "date", "hours", "minutes" or "seconds". A blank value or the
    literal "now" resolves to the current moment, which is always known to
    full precision, so it returns "seconds". Returns None only for a
    time-only value (no explicit date component), since that's genuinely
    ambiguous about the intended date granularity.
    """
    stripped = value.strip()
    if not stripped or stripped.lower() == "now":
        return "seconds"

    head, _, tail = stripped.rpartition(" ")
    body = head if head and _looks_like_zone_name(tail) else stripped
    body = body.replace("Z", "+00:00")

    match = _DATE_PRECISION_RE.match(body)
    if match is None:
        return None

    if match.group("hh") is None:
        return "date"
    if match.group("mm") is None:
        return "hours"
    if match.group("ss") is None:
        return "minutes"
    return "seconds"


def _finer_precision(a: str, b: str) -> str:
    """Return whichever of two date precisions is the more granular."""
    return a if _DATE_PRECISION_RANK[a] >= _DATE_PRECISION_RANK[b] else b


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO 8601 date/time, or a time-only value (defaults to today).

    Accepts a trailing "Z" as shorthand for UTC, a numeric offset such as
    "+02:00", or a space-separated IANA timezone name such as
    "Europe/Oslo" -- only one of these at a time.
    """
    original = value.strip()
    value = original
    tz = None

    head, _, tail = value.rpartition(" ")
    if head and _looks_like_zone_name(tail):
        value, tz_name = head, tail
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError as exc:
            msg = f"{tz_name!r} is not a known timezone name"
            raise click.BadParameter(msg) from exc

    value = value.replace("Z", "+00:00")

    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        with suppress(ValueError):
            parsed = datetime.combine(
                datetime.now(tz=datetime.now().astimezone().tzinfo),
                time.fromisoformat(value),
            )

    if parsed is None:
        msg = f"{original!r} is not a valid ISO 8601 date/time or hh:mm:ss"
        raise click.BadParameter(msg)

    if tz is not None:
        if parsed.tzinfo is not None:
            msg = f"{original!r} specifies both a UTC offset and a timezone name"
            raise click.BadParameter(msg)
        parsed = parsed.replace(tzinfo=tz)

    return parsed


def _resolve_datetime(value: str) -> datetime:
    """Resolve a value to a datetime, treating blank or "now" as the current time."""
    if not value.strip() or value.strip().lower() == "now":
        return datetime.now()  # noqa: DTZ005
    return _parse_datetime(value)


def _pluralize(value: int, unit: str) -> str:
    """Return a string with the value and unit, pluralized if necessary."""
    return f"{value} {unit}{'s' if value != 1 else ''}"


def _format_fractional_hours(seconds: float) -> str:
    """Format a number of seconds as a fractional number of hours."""
    hours = seconds / 3600
    formatted_value = f"{hours:.2f}".rstrip("0").rstrip(".")
    unit = "hour" if formatted_value == "1" else "hours"
    return f"{formatted_value} {unit}"


def _calendar_components(
    a: datetime, b: datetime
) -> tuple[int, int, int, int, int, int]:
    """Break the difference between a and b (a <= b) into calendar components.

    Returns (years, months, days, hours, minutes, seconds).
    """
    years = b.year - a.year
    months = b.month - a.month
    days = b.day - a.day
    hours = b.hour - a.hour
    minutes = b.minute - a.minute
    seconds = b.second - a.second

    if seconds < 0:
        seconds += 60
        minutes -= 1
    if minutes < 0:
        minutes += 60
        hours -= 1
    if hours < 0:
        hours += 24
        days -= 1
    if days < 0:
        prev_month = b.month - 1 or 12
        prev_year = b.year if b.month > 1 else b.year - 1
        days += calendar.monthrange(prev_year, prev_month)[1]
        months -= 1
    if months < 0:
        months += 12
        years -= 1

    return years, months, days, hours, minutes, seconds


def _format_calendar_delta(a: datetime, b: datetime, precision: str) -> str:
    """Format the calendar-based difference between a and b (a <= b).

    Always includes years, months and days; hours, minutes and seconds are
    added progressively depending on precision ("date", "hours", "minutes"
    or "seconds").
    """
    years, months, days, hours, minutes, seconds = _calendar_components(a, b)
    parts = [
        _pluralize(years, "year"),
        _pluralize(months, "month"),
        _pluralize(days, "day"),
    ]
    if precision != "date":
        parts.append(_pluralize(hours, "hour"))
    if precision in ("minutes", "seconds"):
        parts.append(_pluralize(minutes, "minute"))
    if precision == "seconds":
        parts.append(_pluralize(seconds, "second"))
    return ", ".join(parts)


def _format_timedelta(seconds: float, output_format: str = "hours") -> str:
    """Format a timedelta in seconds as a human-readable string."""
    if output_format == "fractions":
        return _format_fractional_hours(seconds)

    seconds = int(seconds)

    if output_format == "seconds":
        return _pluralize(seconds, "second")

    if output_format == "minutes":
        minutes, seconds = divmod(seconds, 60)
        return f"{_pluralize(minutes, 'minute')}, {_pluralize(seconds, 'second')}"

    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return (
        f"{_pluralize(hours, 'hour')}, "
        f"{_pluralize(minutes, 'minute')}, "
        f"{_pluralize(seconds, 'second')}"
    )


@click.command()
@click.version_option(package_name="timedelta")
@click.option(
    "--start",
    "-s",
    default="",
    show_default=False,
    prompt="Start point in time (leave blank or type 'now' for current time)",
    help=(
        "Start point in time (full datetime or just hh:mm:ss for today). "
        "Leave blank or use 'now' for the current time. Specify a "
        "timezone with a trailing Z (UTC), a numeric offset (e.g. "
        "+02:00), or a space-separated IANA name (e.g. "
        "'10:00:00 Europe/Oslo') -- only one at a time; defaults to "
        "naive/local time if omitted."
    ),
)
@click.option(
    "--end",
    "-e",
    default="",
    show_default=False,
    prompt="End point in time (leave blank or type 'now' for current time)",
    help=(
        "End point in time (full datetime or just hh:mm:ss for today). "
        "Leave blank or use 'now' for the current time. Specify a "
        "timezone with a trailing Z (UTC), a numeric offset (e.g. "
        "+02:00), or a space-separated IANA name (e.g. "
        "'12:30:00 Europe/Oslo') -- only one at a time; defaults to "
        "naive/local time if omitted."
    ),
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["seconds", "minutes", "hours", "fractions"]),
    default=None,
    show_default=False,
    help=(
        "Output format: seconds; minutes and seconds; hours, minutes and "
        "seconds; or a fractional number of hours (e.g. '2.5 hours'). If "
        "omitted, and both --start and --end resolve to a known date "
        "(an explicit date, or blank/'now'), a calendar breakdown (years, "
        "months, days, and progressively hours, minutes, seconds) matching "
        "the finer of the two input's granularity is used instead; "
        "otherwise (e.g. a bare time of day such as '10:00:00' on either "
        "side) defaults to hours."
    ),
)
def main(start: str, end: str, output_format: str | None) -> None:
    """Compute the difference between two points in time."""
    start_precision = _input_date_precision(start)
    end_precision = _input_date_precision(end)

    start_dt = _resolve_datetime(start)
    end_dt = _resolve_datetime(end)

    delta = end_dt - start_dt
    direction = "before" if delta.total_seconds() < 0 else "after"

    if output_format is not None:
        formatted = _format_timedelta(abs(delta.total_seconds()), output_format)
    elif start_precision is not None and end_precision is not None:
        precision = _finer_precision(start_precision, end_precision)
        earlier, later = (
            (start_dt, end_dt) if start_dt <= end_dt else (end_dt, start_dt)
        )
        formatted = _format_calendar_delta(earlier, later, precision)
    else:
        formatted = _format_timedelta(abs(delta.total_seconds()), "hours")

    click.echo(f"Time delta: {formatted} ({direction})")
