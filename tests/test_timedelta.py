# Copyright (c) 2026 Stig B. Dørmænen
"""Tests for the timedelta CLI."""

from datetime import date, datetime

import click
import pytest
from click.testing import CliRunner

from timedelta import (
    _format_timedelta,
    _looks_like_zone_name,
    _parse_datetime,
    _pluralize,
    main,
)

EXIT_CODE_USAGE_ERROR = 2


class TestLooksLikeZoneName:
    """Tests for _looks_like_zone_name."""

    @pytest.mark.parametrize("token", ["UTC", "GMT", "Europe/Oslo", "America/New_York"])
    def test_recognizes_zone_names(self, token: str) -> None:
        """It should recognize known zone name patterns."""
        assert _looks_like_zone_name(token) is True

    @pytest.mark.parametrize("token", ["10:00:00", "+02:00", "Z", "notazone"])
    def test_rejects_non_zone_names(self, token: str) -> None:
        """It should reject tokens that are not zone names."""
        assert _looks_like_zone_name(token) is False


class TestParseDatetime:
    """Tests for _parse_datetime."""

    def test_full_datetime(self) -> None:
        """It should parse a full ISO 8601 datetime."""
        assert _parse_datetime("2024-01-01T10:00:00") == datetime(2024, 1, 1, 10, 0, 0)  # noqa: DTZ001

    def test_time_only_defaults_to_today(self) -> None:
        """It should default to today's date when only a time is given."""
        parsed = _parse_datetime("10:00:00")
        assert parsed.date() == date.today()  # noqa: DTZ011
        assert parsed.timetuple()[3:6] == (10, 0, 0)

    def test_trailing_z_means_utc(self) -> None:
        """It should treat a trailing Z as UTC."""
        parsed = _parse_datetime("10:00:00Z")
        offset = parsed.utcoffset()
        assert offset is not None
        assert offset.total_seconds() == 0

    def test_numeric_offset(self) -> None:
        """It should parse a numeric UTC offset."""
        parsed = _parse_datetime("10:00:00+02:00")
        offset = parsed.utcoffset()
        assert offset is not None
        assert offset.total_seconds() == 7200

    def test_time_only_with_zone_name(self) -> None:
        """It should attach an IANA timezone to a time-only value."""
        parsed = _parse_datetime("10:00:00 Europe/Oslo")
        assert parsed.tzinfo is not None
        assert parsed.date() == date.today()  # noqa: DTZ011

    def test_full_datetime_with_zone_name(self) -> None:
        """It should attach an IANA timezone to a full datetime value."""
        parsed = _parse_datetime("2024-06-01T10:00:00 Europe/Oslo")
        offset = parsed.utcoffset()
        assert offset is not None
        assert offset.total_seconds() == 7200

    def test_unknown_zone_name_raises(self) -> None:
        """It should raise BadParameter for an unknown timezone name."""
        with pytest.raises(click.BadParameter, match="is not a known timezone name"):
            _parse_datetime("10:00:00 Not/AZone")

    def test_offset_and_zone_name_conflict_raises(self) -> None:
        """It should raise BadParameter when both offset and zone name are given."""
        with pytest.raises(click.BadParameter, match="specifies both"):
            _parse_datetime("10:00:00+02:00 Europe/Oslo")

    def test_invalid_value_raises(self) -> None:
        """It should raise BadParameter for values that are not parseable."""
        with pytest.raises(click.BadParameter, match="is not a valid ISO 8601"):
            _parse_datetime("notadate")


class TestPluralize:
    """Tests for _pluralize."""

    def test_singular(self) -> None:
        """It should not append an s for a value of 1."""
        assert _pluralize(1, "second") == "1 second"

    @pytest.mark.parametrize("value", [0, 2])
    def test_plural(self, value: int) -> None:
        """It should append an s for values other than 1."""
        assert _pluralize(value, "second") == f"{value} seconds"


class TestFormatTimedelta:
    """Tests for _format_timedelta."""

    def test_seconds_format(self) -> None:
        """It should format as seconds only."""
        assert _format_timedelta(125, "seconds") == "125 seconds"

    def test_minutes_format(self) -> None:
        """It should format as minutes and seconds."""
        assert _format_timedelta(125, "minutes") == "2 minutes, 5 seconds"

    def test_hours_format_default(self) -> None:
        """It should default to hours, minutes and seconds."""
        assert _format_timedelta(9045) == "2 hours, 30 minutes, 45 seconds"

    def test_hours_format_explicit(self) -> None:
        """It should format as hours, minutes and seconds when requested."""
        assert _format_timedelta(9045, "hours") == "2 hours, 30 minutes, 45 seconds"

    def test_zero_seconds(self) -> None:
        """It should format a zero delta."""
        assert _format_timedelta(0, "seconds") == "0 seconds"


class TestMain:
    """Tests for the main CLI command."""

    def test_options_after_direction(self) -> None:
        """It should report 'after' when end is later than start."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["-s", "2024-01-01T10:00:00", "-e", "2024-01-03T12:30:45"],
        )
        assert result.exit_code == 0
        expected = "Time delta: 50 hours, 30 minutes, 45 seconds (after)"
        assert result.output.strip() == expected

    def test_options_before_direction(self) -> None:
        """It should report 'before' when end is earlier than start."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["-s", "2024-01-03T12:30:45", "-e", "2024-01-01T10:00:00"],
        )
        assert result.exit_code == 0
        expected = "Time delta: 50 hours, 30 minutes, 45 seconds (before)"
        assert result.output.strip() == expected

    def test_seconds_format_option(self) -> None:
        """It should honor the seconds output format."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["-s", "10:00:00", "-e", "10:02:05", "-f", "seconds"],
        )
        assert result.exit_code == 0
        assert result.output.strip() == "Time delta: 125 seconds (after)"

    def test_minutes_format_option(self) -> None:
        """It should honor the minutes output format."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["-s", "10:00:00", "-e", "10:02:05", "-f", "minutes"],
        )
        assert result.exit_code == 0
        assert result.output.strip() == "Time delta: 2 minutes, 5 seconds (after)"

    def test_prompts_when_options_missing(self) -> None:
        """It should prompt for start and end when not given as options."""
        runner = CliRunner()
        result = runner.invoke(main, input="10:00:00\n10:05:30\n")
        assert result.exit_code == 0
        assert "Time delta: 0 hours, 5 minutes, 30 seconds (after)" in result.output

    def test_invalid_start_value_errors(self) -> None:
        """It should exit with a usage error for an invalid start value."""
        runner = CliRunner()
        result = runner.invoke(main, ["-s", "notadate", "-e", "10:00:00"])
        assert result.exit_code == EXIT_CODE_USAGE_ERROR
        assert "is not a valid ISO 8601" in result.output

    def test_invalid_choice_for_format(self) -> None:
        """It should exit with a usage error for an invalid format choice."""
        runner = CliRunner()
        result = runner.invoke(main, ["-s", "10:00:00", "-e", "12:00:00", "-f", "days"])
        assert result.exit_code == EXIT_CODE_USAGE_ERROR
