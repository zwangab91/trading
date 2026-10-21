#!/bin/bash
set -euo pipefail

# Only run in Claude Code cloud sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Python package with all optional extras (backend, dashboard, research, test)
python3 -m pip install --quiet -e ".[research,test,dashboard,backend]"

# Next.js frontend
if [ -f frontend/package.json ]; then
  (cd frontend && npm install --no-audit --no-fund)
fi
