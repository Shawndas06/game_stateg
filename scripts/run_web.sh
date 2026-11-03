#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo 'Create the environment: python3.12 -m venv .venv'
  exit 1
fi
if [[ ! -f web/dist/index.html ]]; then
  echo 'Build the client: cd web && npm ci && npm run build'
  exit 1
fi
exec .venv/bin/python -m uvicorn server.app:create_app --factory --host 127.0.0.1 --port "${PORT:-8000}"
