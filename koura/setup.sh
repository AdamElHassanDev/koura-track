#!/usr/bin/env bash
# One-time setup: Python 3.12 environment and the patched map generator.
# Needs: git, curl, and either `uv` or a `python3.12` on the PATH.
set -euo pipefail
cd "$(dirname "$0")/.."
PIN=d9e713c66c01417fb035c65b81d77093094742c6

if [ ! -d openlaps/.git ]; then
  git clone https://github.com/theopenlaps/openlaps openlaps
  git -C openlaps checkout -q -b koura "$PIN"
  git -C openlaps apply --index ../koura/openlaps_koura.patch
  echo "generator: openlaps at $PIN with koura/openlaps_koura.patch applied"
fi

if [ ! -x .venv/bin/python ]; then
  if command -v uv >/dev/null; then uv venv --python 3.12 .venv; PIP="uv pip install --python .venv/bin/python"
  else python3.12 -m venv .venv; PIP=".venv/bin/pip install"; fi
  $PIP -r openlaps/requirements.txt
  $PIP -e openlaps
fi
echo "ready. Build the kart track alone (1 minute):"
echo "  (ulimit -v 8000000; .venv/bin/python koura/build.py K --name kart_test)"
