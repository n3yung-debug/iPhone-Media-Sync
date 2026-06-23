#!/bin/bash
# SessionStart hook: install dependencies so tests/linters work in
# Claude Code on the web. Safe to run multiple times.
set -euo pipefail

# Only run in the remote (web) environment; local machines manage their own env.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Make the src/ layout importable for the whole session.
echo 'export PYTHONPATH="$CLAUDE_PROJECT_DIR/src"' >> "$CLAUDE_ENV_FILE"

# Test/dev tooling.
python3 -m pip install --quiet pytest ruff

# Runtime dependencies. PySide6 is a large GUI download and isn't needed to run
# the test suite (the core logic is Qt-free), so don't fail the session if the
# full set can't install here; the tests only require the core.
python3 -m pip install --quiet -r requirements.txt || \
  echo "note: full requirements (incl. PySide6) did not all install; core tests still run."
