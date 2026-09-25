# Maintaining the man page

`timedelta.1` is a hand-written [groff](https://www.gnu.org/software/groff/)
man page. It is **not** auto-generated -- [click-man](https://github.com/click-contrib/click-man),
the usual tool for generating man pages from Click CLIs, is unmaintained and
incompatible with modern `importlib.metadata`, so this file must be kept in
sync manually whenever the CLI changes.

## Updating the content

1. Edit `timedelta.1` directly using standard groff/troff macros:
   - `.TP` starts a new option/term entry
   - `.B` / `.BR` / `.I` / `.IR` render bold/italic text (used for option
     names and placeholders)
   - `.RS` / `.IP \(bu 2` / `.RE` render a bullet list (see the `--format`
     choices for an example)
   - Escape literal hyphens as `\-`. This is required for correct rendering
     and is also relied on by the automated consistency check (see below).

2. Preview your changes locally:

   ```console
   uv run poe man-preview
   ```

3. Validate the groff syntax (catches warnings/errors before committing):

   ```console
   man --warnings -E UTF-8 -l timedelta.1 >/dev/null
   ```

4. Keep the version in sync. The third field of the `.TH` header
   (`"timedelta X.Y.Z"`) must match the `version` in `pyproject.toml`.
   Update it whenever the project version is bumped.

## Verifying consistency

`tests/test_man_page.py` runs as part of `uv run poe test` (and therefore
`uv run poe release` and CI) and fails the build if:

- the `.TH` header version does not match the installed package version, or
- any CLI option/flag (`-s`/`--start`, `-e`/`--end`, `-f`/`--format`,
  `--version`) or `--format` choice (`seconds`, `minutes`, `hours`,
  `fractions`) is not mentioned anywhere in this file.

These checks are derived dynamically from the Click command definition, so
adding, renaming, or removing an option will be caught automatically -- but
the *content* of the man page (descriptions, examples, wording) is not
verified and must be reviewed by hand.

Run the full check locally with:

```console
uv run poe test
```
