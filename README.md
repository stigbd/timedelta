# timedelta

[![Release pipeline](https://github.com/stigbd/timedelta/actions/workflows/release.yml/badge.svg)](https://github.com/stigbd/timedelta/actions/workflows/release.yml)

A minimal CLI for computing the time delta between two points in time, built
with [Click](https://click.palletsprojects.com/).

## Installation

Install it as an isolated, globally available command using
[pipx](https://pipx.pypa.io/) (recommended):

```console
pipx install .
```

Or, from the published package once available on PyPI:

```console
pipx install timedelta
```

If you already use [uv](https://docs.astral.sh/uv/), its `uv tool` command
works the same way:

```console
uv tool install .
```

Once installed, the `timedelta` command is available on your `PATH`:

```console
timedelta --help
```

## Usage

Alternatively, run it directly from the project without installing, via uv:

```console
uv run timedelta
```

You'll be prompted for `--start` and `--end` if not given as options. If
either is omitted, or left blank at its prompt, the current time is used.
You can also use the literal `now` for either `--start` or `--end`:

```console
uv run timedelta --start 2024-01-01T10:00:00 --end 2024-01-01T12:30:00
# Time delta: 2 hours, 30 minutes, 0 seconds (after)

uv run timedelta --start 2024-01-01T10:00:00
# Time delta: <time since start> (after)

uv run timedelta --start 08:49 --end now
# Time delta: <time since 08:49> (after)

uv run timedelta --start now --end 20:00:00
# Time delta: <time until 20:00> (after)
```

### Input formats

- Full ISO 8601 datetime: `2024-01-01T10:00:00`
- Time only (defaults to today's date): `10:00:00`
- The literal `now` (case-insensitive) for the current time
- Timezone via trailing `Z` (UTC), a numeric offset (`+02:00`), or a
  space-separated IANA name (`10:00:00 Europe/Oslo`) -- only one at a time

### Output format

Use `-f`/`--format` to control the level of detail:

| Format      | Example output                    |
| ----------- | ---------------------------------- |
| `seconds`   | `9045 seconds`                     |
| `minutes`   | `150 minutes, 45 seconds`          |
| `hours`     | `2 hours, 30 minutes, 45 seconds` (default) |
| `fractions` | `2.5 hours`                        |

```console
uv run timedelta -s 10:00:00 -e 12:30:45 -f seconds
```

Run `uv run timedelta --help` for the full option reference, or
`uv run timedelta --version` to print the installed version.

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management
and [poethepoet](https://poethepoet.natn.io/) for task running.

### Setup

```console
uv sync
```

### Common tasks

| Command              | Description                              |
| --------------------- | ----------------------------------------- |
| `uv run poe format`   | Format code with ruff                     |
| `uv run poe lint`     | Lint (and auto-fix) with ruff             |
| `uv run poe typecheck`| Type-check with ty                        |
| `uv run poe test`     | Run tests with pytest and coverage        |
| `uv run poe check-deps` | Check for unused/missing deps with deptry |
| `uv run poe audit`    | Audit dependencies for vulnerabilities    |
| `uv run poe release`  | Run lint, typecheck and test in sequence  |

Tests live in `tests/` and require 100% coverage (enforced via
`pyproject.toml`).

## License

This project is licensed under the [MIT License](LICENSE).

