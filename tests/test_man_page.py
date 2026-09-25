# Copyright (c) 2026 Stig B. Dørmænen
"""Consistency checks between the man page and the CLI definition."""

import re
from importlib.metadata import version as installed_version
from pathlib import Path

import click
import pytest

from timedelta import main

MAN_PAGE = Path(__file__).resolve().parent.parent / "man" / "timedelta.1"

ALL_OPTS = sorted({opt for param in main.params for opt in param.opts})

FORMAT_PARAM = next(param for param in main.params if param.name == "output_format")
assert isinstance(FORMAT_PARAM.type, click.Choice)
FORMAT_CHOICES = FORMAT_PARAM.type.choices


def _escape_option(opt: str) -> str:
    """Return the option string as it appears escaped in the troff source."""
    return opt.replace("-", r"\-")


@pytest.fixture(scope="module")
def man_page_text() -> str:
    """Return the raw contents of the man page."""
    return MAN_PAGE.read_text(encoding="utf-8")


class TestManPage:
    """Consistency checks between the man page and the CLI definition."""

    def test_man_page_exists(self) -> None:
        """The man page file should exist in the repository."""
        assert MAN_PAGE.is_file()

    def test_version_matches_package_version(self, man_page_text: str) -> None:
        """The .TH header version should match the installed package version."""
        match = re.search(
            r'\.TH\s+\S+\s+\d+\s+"[^"]*"\s+"timedelta\s+([^"]+)"',
            man_page_text,
        )
        assert match is not None, "Could not find version in .TH header"
        assert match.group(1) == installed_version("timedelta")

    @pytest.mark.parametrize("opt", ALL_OPTS)
    def test_all_options_documented(self, man_page_text: str, opt: str) -> None:
        """Every CLI option/flag should be mentioned in the man page."""
        assert _escape_option(opt) in man_page_text

    @pytest.mark.parametrize("choice", FORMAT_CHOICES)
    def test_all_format_choices_documented(
        self,
        man_page_text: str,
        choice: str,
    ) -> None:
        """Every --format choice should be mentioned in the man page."""
        assert choice in man_page_text
