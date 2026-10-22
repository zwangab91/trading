#!/bin/bash
set -euo pipefail

# Only run in Claude Code cloud sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Python package with all optional extras (backend, dashboard, research, test)
python3 -m pip install --quiet -e ".[research,test,dashboard,backend]"

# Next.js frontend. npm ci installs exactly what the lockfile pins and never
# rewrites it; skip it when node_modules is already newer than the lockfile.
if [ -f frontend/package-lock.json ]; then
  if [ ! -f frontend/node_modules/.package-lock.json ] \
    || [ frontend/package-lock.json -nt frontend/node_modules/.package-lock.json ]; then
    (cd frontend && npm ci --no-audit --no-fund)
  fi
fi
