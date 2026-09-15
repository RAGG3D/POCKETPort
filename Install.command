#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 scripts/install.py
printf '\nInstallation finished. Press Enter to close. '
read -r answer
