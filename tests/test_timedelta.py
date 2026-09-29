# Copyright (c) 2026 Stig B. Dørmænen
"""Tests for the timedelta CLI."""

from datetime import date, datetime, tzinfo

import click
import pytest
from click.testing import CliRunner

import timedelta as timedelta_module
from timedelta import (
    _calendar_components,
    _finer_precision,
    _format_calendar_delta,
    _format_fractional_hours,
    _format_timedelta,
    _input_date_precision,
    _looks_like_zone_name,
    _parse_datetime,
    _pluralize,
    _resolve_datetime,
    main,
)

EXIT_CODE_USAGE_ERROR = 2


class FrozenDatetime(datetime):
    """A datetime subclass with a fixed `now()` for deterministic tests."""

    @classmethod
    def now(cls, tz: tzinfo | None = None) -> FrozenDatetime:  # noqa: ARG003
        return cls(2024, 1, 1, 12, 30, 0)


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


class TestResolveDatetime:
    """Tests for _resolve_datetime."""

    def test_blank_resolves_to_now(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """It should resolve a blank value to the current time."""
        monkeypatch.setattr(timedelta_module, "datetime", FrozenDatetime)
        assert _resolve_datetime("") == FrozenDatetime(2024, 1, 1, 12, 30, 0)

    @pytest.mark.parametrize("value", ["now", "NOW", " Now "])
    def test_now_literal_resolves_to_now(
        self,
        monkeypatch: pytest.MonkeyPatch,
        value: str,
    ) -> None:
        """It should resolve the literal 'now' (any case) to the current time."""
        monkeypatch.setattr(timedelta_module, "datetime", FrozenDatetime)
        assert _resolve_datetime(value) == FrozenDatetime(2024, 1, 1, 12, 30, 0)

    def test_other_values_are_parsed(self) -> None:
        """It should parse non-'now' values normally."""
        expected = datetime(2024, 1, 1, 10, 0, 0)  # noqa: DTZ001
        assert _resolve_datetime("2024-01-01T10:00:00") == expected


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

    def test_fractions_format(self) -> None:
        """It should format as a fractional number of hours."""
        assert _format_timedelta(9000, "fractions") == "2.5 hours"


class TestFormatFractionalHours:
    """Tests for _format_fractional_hours."""

    def test_fraction(self) -> None:
        """It should format a fractional value with trailing zeros stripped."""
        assert _format_fractional_hours(9000) == "2.5 hours"

    def test_whole_hour(self) -> None:
        """It should format a whole number of hours without a decimal point."""
        assert _format_fractional_hours(7200) == "2 hours"

    def test_singular_hour(self) -> None:
        """It should use the singular unit for exactly one hour."""
        assert _format_fractional_hours(3600) == "1 hour"


class TestMain:
    """Tests for the main CLI command."""

    def test_version_option(self) -> None:
        """It should print the package version and exit."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"], prog_name="timedelta")
        assert result.exit_code == 0
        assert "timedelta, version" in result.output

    def test_options_after_direction(self) -> None:
        """It should report 'after' when end is later than start."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["-s", "2024-01-01T10:00:00", "-e", "2024-01-03T12:30:45", "-f", "hours"],
        )
        assert result.exit_code == 0
        expected = "Time delta: 50 hours, 30 minutes, 45 seconds (after)"
        assert result.output.strip() == expected

    def test_options_before_direction(self) -> None:
        """It should report 'before' when end is earlier than start."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["-s", "2024-01-03T12:30:45", "-e", "2024-01-01T10:00:00", "-f", "hours"],
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

    def test_prompts_for_start_when_option_missing(self) -> None:
        """It should prompt for start when not given as an option."""
        runner = CliRunner()
        result = runner.invoke(main, ["-e", "10:05:30"], input="10:00:00\n")
        assert result.exit_code == 0
        assert "Time delta: 0 hours, 5 minutes, 30 seconds (after)" in result.output

    def test_prompts_for_both_start_and_end_when_omitted(self) -> None:
        """It should prompt for both start and end when neither is given."""
        runner = CliRunner()
        result = runner.invoke(main, input="10:00:00\n10:05:30\n")
        assert result.exit_code == 0
        assert "Time delta: 0 hours, 5 minutes, 30 seconds (after)" in result.output

    def test_end_defaults_to_current_time_when_omitted(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """It should use the current time when --end is not given."""
        monkeypatch.setattr(timedelta_module, "datetime", FrozenDatetime)
        runner = CliRunner()
        result = runner.invoke(main, ["-s", "2024-01-01T10:00:00"], input="\n")
        assert result.exit_code == 0
        expected = (
            "Time delta: 0 years, 0 months, 0 days, "
            "2 hours, 30 minutes, 0 seconds (after)"
        )
        assert result.output.strip().endswith(expected)

    def test_start_defaults_to_current_time_when_omitted(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """It should use the current time when --start is left blank."""
        monkeypatch.setattr(timedelta_module, "datetime", FrozenDatetime)
        runner = CliRunner()
        result = runner.invoke(main, ["-e", "2024-01-01T15:00:00"], input="\n")
        assert result.exit_code == 0
        expected = (
            "Time delta: 0 years, 0 months, 0 days, "
            "2 hours, 30 minutes, 0 seconds (after)"
        )
        assert result.output.strip().endswith(expected)

    def test_end_now_literal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """It should treat -e now as the current time."""
        monkeypatch.setattr(timedelta_module, "datetime", FrozenDatetime)
        runner = CliRunner()
        result = runner.invoke(main, ["-s", "2024-01-01T10:00:00", "-e", "now"])
        assert result.exit_code == 0
        expected = (
            "Time delta: 0 years, 0 months, 0 days, "
            "2 hours, 30 minutes, 0 seconds (after)"
        )
        assert result.output.strip() == expected

    def test_start_now_literal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """It should treat -s now as the current time."""
        monkeypatch.setattr(timedelta_module, "datetime", FrozenDatetime)
        runner = CliRunner()
        result = runner.invoke(main, ["-s", "now", "-e", "2024-01-01T15:00:00"])
        assert result.exit_code == 0
        expected = (
            "Time delta: 0 years, 0 months, 0 days, "
            "2 hours, 30 minutes, 0 seconds (after)"
        )
        assert result.output.strip() == expected

    def test_fractions_format_option(self) -> None:
        """It should honor the fractions output format."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["-s", "10:00:00", "-e", "12:30:00", "-f", "fractions"],
        )
        assert result.exit_code == 0
        assert result.output.strip() == "Time delta: 2.5 hours (after)"

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

    def test_auto_calendar_format_full_precision(self) -> None:
        """It should auto-select a full calendar breakdown for full datetimes."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["-s", "2024-01-01T10:00:00", "-e", "2024-01-03T12:30:45"],
        )
        assert result.exit_code == 0
        expected = (
            "Time delta: 0 years, 0 months, 2 days, "
            "2 hours, 30 minutes, 45 seconds (after)"
        )
        assert result.output.strip() == expected

    def test_auto_calendar_format_date_only(self) -> None:
        """It should auto-select years/months/days only for date-only inputs."""
        runner = CliRunner()
        result = runner.invoke(main, ["-s", "2024-01-01", "-e", "2024-03-05"])
        assert result.exit_code == 0
        expected = "Time delta: 0 years, 2 months, 4 days (after)"
        assert result.output.strip() == expected

    def test_auto_calendar_format_hours_precision(self) -> None:
        """It should include hours when input is given down to the hour."""
        runner = CliRunner()
        result = runner.invoke(main, ["-s", "2024-01-01T08", "-e", "2024-01-02T10"])
        assert result.exit_code == 0
        expected = "Time delta: 0 years, 0 months, 1 day, 2 hours (after)"
        assert result.output.strip() == expected

    def test_auto_calendar_format_minutes_precision(self) -> None:
        """It should include hours and minutes when input is given to the minute."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["-s", "2024-01-01T08:15", "-e", "2024-01-02T10:45"]
        )
        assert result.exit_code == 0
        expected = "Time delta: 0 years, 0 months, 1 day, 2 hours, 30 minutes (after)"
        assert result.output.strip() == expected

    def test_auto_calendar_format_mixed_precision_uses_finer(self) -> None:
        """It should use the finer of two differing input precisions."""
        runner = CliRunner()
        result = runner.invoke(main, ["-s", "2024-01-01", "-e", "2024-01-03T12:30:45"])
        assert result.exit_code == 0
        expected = (
            "Time delta: 0 years, 0 months, 2 days, "
            "12 hours, 30 minutes, 45 seconds (after)"
        )
        assert result.output.strip() == expected

    def test_explicit_format_overrides_auto_calendar(self) -> None:
        """An explicit -f/--format should override auto-detected calendar format."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["-s", "2024-01-01T10:00:00", "-e", "2024-01-03T12:30:45", "-f", "seconds"],
        )
        assert result.exit_code == 0
        assert result.output.strip() == "Time delta: 181845 seconds (after)"

    def test_time_only_inputs_keep_legacy_hours_default(self) -> None:
        """Time-only inputs (no explicit date) should keep the legacy hours default."""
        runner = CliRunner()
        result = runner.invoke(main, ["-s", "10:00:00", "-e", "12:30:45"])
        assert result.exit_code == 0
        assert (
            result.output.strip()
            == "Time delta: 2 hours, 30 minutes, 45 seconds (after)"
        )


class TestInputDatePrecision:
    """Tests for _input_date_precision."""

    def test_blank_returns_seconds(self) -> None:
        """It should return 'seconds' for a blank value (resolves to now)."""
        assert _input_date_precision("") == "seconds"

    @pytest.mark.parametrize("value", ["now", "NOW", " Now "])
    def test_now_returns_seconds(self, value: str) -> None:
        """It should return 'seconds' for the literal 'now'."""
        assert _input_date_precision(value) == "seconds"

    @pytest.mark.parametrize("value", ["10:00:00", "10:00", "10:00:00 Europe/Oslo"])
    def test_time_only_returns_none(self, value: str) -> None:
        """It should return None for time-only values (no explicit date)."""
        assert _input_date_precision(value) is None

    def test_date_only(self) -> None:
        """It should return 'date' for a bare date."""
        assert _input_date_precision("2024-01-01") == "date"

    def test_date_with_hour(self) -> None:
        """It should return 'hours' when only the hour is given."""
        assert _input_date_precision("2024-01-01T10") == "hours"

    def test_date_with_hour_and_minute(self) -> None:
        """It should return 'minutes' when hour and minute are given."""
        assert _input_date_precision("2024-01-01T10:00") == "minutes"

    def test_full_datetime(self) -> None:
        """It should return 'seconds' for a full datetime."""
        assert _input_date_precision("2024-01-01T10:00:00") == "seconds"

    def test_full_datetime_with_offset(self) -> None:
        """It should still return 'seconds' when a numeric offset is appended."""
        assert _input_date_precision("2024-01-01T10:00:00+02:00") == "seconds"

    def test_full_datetime_with_zone_name(self) -> None:
        """It should still return 'seconds' when a zone name is appended."""
        assert _input_date_precision("2024-01-01T10:00:00 Europe/Oslo") == "seconds"

    def test_invalid_value_returns_none(self) -> None:
        """It should return None for an unparseable value."""
        assert _input_date_precision("notadate") is None


class TestFinerPrecision:
    """Tests for _finer_precision."""

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            ("date", "seconds", "seconds"),
            ("seconds", "date", "seconds"),
            ("hours", "minutes", "minutes"),
            ("seconds", "seconds", "seconds"),
        ],
    )
    def test_returns_finer_of_two(self, a: str, b: str, expected: str) -> None:
        """It should return whichever precision is more granular."""
        assert _finer_precision(a, b) == expected


class TestCalendarComponents:
    """Tests for _calendar_components."""

    def test_simple_difference(self) -> None:
        """It should compute a straightforward calendar difference."""
        a = datetime(2024, 1, 1, 10, 0, 0)  # noqa: DTZ001
        b = datetime(2024, 1, 3, 12, 30, 45)  # noqa: DTZ001
        assert _calendar_components(a, b) == (0, 0, 2, 2, 30, 45)

    def test_borrows_across_month_boundary(self) -> None:
        """It should borrow days from the previous month when needed."""
        a = datetime(2024, 1, 20, 0, 0, 0)  # noqa: DTZ001
        b = datetime(2024, 3, 5, 0, 0, 0)  # noqa: DTZ001
        assert _calendar_components(a, b) == (0, 1, 14, 0, 0, 0)

    def test_borrows_across_year_boundary(self) -> None:
        """It should borrow months from the previous year when needed."""
        a = datetime(2023, 11, 1, 0, 0, 0)  # noqa: DTZ001
        b = datetime(2024, 1, 1, 0, 0, 0)  # noqa: DTZ001
        assert _calendar_components(a, b) == (0, 2, 0, 0, 0, 0)

    def test_borrows_across_seconds_minutes_and_hours(self) -> None:
        """It should borrow seconds, minutes and hours without touching days."""
        a = datetime(2024, 1, 2, 23, 50, 50)  # noqa: DTZ001
        b = datetime(2024, 1, 3, 0, 10, 20)  # noqa: DTZ001
        assert _calendar_components(a, b) == (0, 0, 0, 0, 19, 30)


class TestFormatCalendarDelta:
    """Tests for _format_calendar_delta."""

    def test_date_precision(self) -> None:
        """It should include only years, months and days for 'date' precision."""
        a = datetime(2024, 1, 1)  # noqa: DTZ001
        b = datetime(2024, 3, 5)  # noqa: DTZ001
        assert _format_calendar_delta(a, b, "date") == "0 years, 2 months, 4 days"

    def test_seconds_precision(self) -> None:
        """It should include all six units for 'seconds' precision."""
        a = datetime(2024, 1, 1, 10, 0, 0)  # noqa: DTZ001
        b = datetime(2024, 1, 3, 12, 30, 45)  # noqa: DTZ001
        expected = "0 years, 0 months, 2 days, 2 hours, 30 minutes, 45 seconds"
        assert _format_calendar_delta(a, b, "seconds") == expected
