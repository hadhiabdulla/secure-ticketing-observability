#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
printf '\nOpen http://127.0.0.1:5000 in your browser. Ctrl+C stops the server.\n'
exec .venv/bin/python app.py
