# Copyright (c) 2026 Stig B. Dørmænen
"""A minimal CLI for computing the time delta between two points in time."""

from contextlib import suppress
from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import click


def _looks_like_zone_name(token: str) -> bool:
    """Return True if token looks like an IANA timezone name (e.g. Europe/Oslo)."""
    return token in ("UTC", "GMT") or "/" in token


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


def _pluralize(value: int, unit: str) -> str:
    """Return a string with the value and unit, pluralized if necessary."""
    return f"{value} {unit}{'s' if value != 1 else ''}"


def _format_timedelta(seconds: float, output_format: str = "hours") -> str:
    """Format a timedelta in seconds as a human-readable string."""
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
@click.option(
    "--start",
    "-s",
    prompt="Start point in time (e.g. 2024-01-01T10:00:00 or 10:00:00)",
    help=(
        "Start point in time (full datetime or just hh:mm:ss for today). "
        "Specify a timezone with a trailing Z (UTC), a numeric offset "
        "(e.g. +02:00), or a space-separated IANA name (e.g. "
        "'10:00:00 Europe/Oslo') -- only one at a time; defaults to "
        "naive/local time if omitted."
    ),
)
@click.option(
    "--end",
    "-e",
    prompt="End point in time (e.g. 2024-01-01T12:30:00 or 12:30:00)",
    help=(
        "End point in time (full datetime or just hh:mm:ss for today). "
        "Specify a timezone with a trailing Z (UTC), a numeric offset "
        "(e.g. +02:00), or a space-separated IANA name (e.g. "
        "'12:30:00 Europe/Oslo') -- only one at a time; defaults to "
        "naive/local time if omitted."
    ),
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["seconds", "minutes", "hours"]),
    default="hours",
    show_default=True,
    help="Output format: seconds; minutes and seconds; or hours, minutes and seconds.",
)
def main(start: str, end: str, output_format: str) -> None:
    """Compute the difference between two points in time."""
    start_dt = _parse_datetime(start)
    end_dt = _parse_datetime(end)

    delta = end_dt - start_dt
    direction = "before" if delta.total_seconds() < 0 else "after"
    formatted = _format_timedelta(abs(delta.total_seconds()), output_format)

    click.echo(f"Time delta: {formatted} ({direction})")
