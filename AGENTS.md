# Agent Instructions

Instructions for AI coding agents (Claude Code, Codex, Copilot, Cursor, and
others) working in this repository. Human contributors should read
[CONTRIBUTING.md](CONTRIBUTING.md); everything there applies to agents too.

## Project

A single-file Prometheus exporter for Pi-hole v6. `pihole6_exporter` is a Python
script with no `.py` extension. It logs in to the Pi-hole API, scrapes stats on
each Prometheus request, and serves them on port 9617. Tests live in `tests/`
and load the script by path through `tests/support.py`.

## Rules

- **Only change the lines your task needs.** Do not strip whitespace, reorder
  imports, re-wrap lines, or reformat code outside the change. Editors and
  agents that "clean up" a whole file on save have produced large
  whitespace-only diffs here before.
- **Run the checks before you finish:**

  ```bash
  pre-commit run --all-files
  coverage run --include=pihole6_exporter -m unittest discover -s tests -v
  coverage report -m --fail-under=95
  ```

- **Test every behavior change.** Mock HTTP with `unittest.mock`; never call a
  real Pi-hole from tests. A bug fix needs a test that fails without the fix.
- **Keep dependencies pinned** to exact versions in `requirements.txt` and
  `requirements-dev.txt`. Do not add a dependency without a clear need.
- **Pin GitHub Actions** and reusable workflows to a full commit SHA with the
  version in a trailing comment, for example
  `actions/checkout@<sha> # v7.0.1`.
- **Do not change metric names, labels, or help text** without calling it out
  as a breaking change; dashboards and alerts depend on them.
- **Commit messages and PR titles** follow Conventional Commits (`fix:`,
  `feat:`, `test:`, `chore:`, `docs:`).
- Never log the API token or session ID.
