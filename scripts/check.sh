#!/usr/bin/env bash
# The one command that must stay green: lint, type check, and tests.
#
# Why a script: Python has no `npm run check`, and CI and people should run the
# same thing. No step loads the model, so it runs anywhere, including CI.
set -euo pipefail
cd "$(dirname "$0")/.."

uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy
uv run --no-sync pytest -q
