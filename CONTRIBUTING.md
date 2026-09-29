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
every commit is checked before it is created. The linters, ruff included, run
through pre-commit, so `requirements-dev.txt` only adds the test tools.

## Running the checks

```bash
# Unit tests with coverage (CI fails below 95%)
coverage run --include=pihole6_exporter -m unittest discover -s tests -v
coverage report -m

# Every linter, on every file
pre-commit run --all-files
```

The tests mock every HTTP call, so you do not need a Pi-hole to run them.

## Pinning

Every dependency is pinned to an immutable hash, not only a version:

- **Python packages:** `requirements.txt` and `requirements-dev.txt` list every
  package, including transitive ones, with `--hash` values, and are installed
  with `pip install --require-hashes`. Edit `requirements.in` or
  `requirements-dev.in`, then regenerate with the `pip-compile` command at the
  top of that file.
- **Container images:** the Dockerfile base image and the Docker-based
  pre-commit hooks use `image:tag@sha256:<digest>`.
- **GitHub Actions and pre-commit hooks:** a full commit SHA with the version in
  a trailing comment, for example `rev: <sha>  # frozen: v6.0.0`.

## What the checks enforce

- **Whitespace:** no trailing whitespace, a final newline in every file, and LF
  line endings. `.editorconfig` sets this up in most editors, `.gitattributes`
  normalizes line endings in git, and pre-commit fixes anything that slips
  through.
- **Python:** [ruff](https://docs.astral.sh/ruff/) lint rules in `ruff.toml`, and
  `ruff format` for code style.
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
