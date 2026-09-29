# Contributing

Thanks for helping improve pihole6-exporter. This page covers how to set up,
what the checks enforce, and what a pull request needs before it can merge.

## Setup

You need Python 3.14, [pre-commit](https://pre-commit.com), and Docker (the
Markdown, Actions, and Dockerfile linters run in containers).

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
```

`pre-commit install` sets up both the `pre-commit` and `commit-msg` hooks, so
every commit is checked before it is created.

## Running the checks

```bash
# Unit tests with coverage (CI fails below 95%)
coverage run --include=pihole6_exporter -m unittest discover -s tests -v
coverage report -m

# Every linter, on every file
pre-commit run --all-files
```

The tests mock every HTTP call, so you do not need a Pi-hole to run them.

## What the checks enforce

- **Whitespace:** no trailing whitespace, a final newline in every file, and LF
  line endings. `.editorconfig` sets this up in most editors, `.gitattributes`
  normalizes line endings in git, and pre-commit fixes anything that slips
  through.
- **Python:** [ruff](https://docs.astral.sh/ruff/) lint rules in `ruff.toml`.
- **YAML, Markdown, GitHub Actions, Dockerfile:** yamllint, markdownlint,
  actionlint, and hadolint.
- **Commit messages:** [Conventional Commits](https://www.conventionalcommits.org/).
  The type sets the next release version: `fix:` is a patch, `feat:` is a
  minor, and `!` or `BREAKING CHANGE:` is a major.

## Pull requests

- Keep each pull request to one change. Do not reformat lines you are not
  otherwise changing; whitespace-only edits to unrelated lines make the diff
  and `git blame` harder to read. If code needs reformatting, do it in its own
  pull request.
- Add or update tests for any behavior you change. A bug fix should include a
  test that fails without the fix.
- Update `README.md` when you add or change a flag, environment variable, or
  metric.
- The pull request title becomes the squashed commit message, so it must also
  follow Conventional Commits.
- CI must pass: pre-commit, unit tests, and the Docker build.

## Releases

Merging to `main` cuts a release automatically from the commit history and
publishes the image to `ghcr.io/mosher-labs/pihole6-exporter` with the version
tags (`1.2.3`, `1.2`, `1`), `sha-<commit>`, and `latest`.
