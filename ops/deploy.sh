#!/usr/bin/env bash
set -euo pipefail
HOST=${1:? "host user@ip required"}
APP_DIR=/opt/Falconer

rsync -az --delete --exclude ".git" --exclude "env" . "$HOST:$APP_DIR"
ssh "$HOST" "cd $APP_DIR && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e . && sudo systemctl restart falconer"