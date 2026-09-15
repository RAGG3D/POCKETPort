#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  printf 'Run Install.command first.\n'
  exit 1
fi
exec .venv/bin/python -m pocketport desktop
