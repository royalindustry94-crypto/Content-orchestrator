#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOG_DIR="/tmp/content-orchestrator-codespace"
LOG_FILE="$LOG_DIR/dev_up.log"
PID_FILE="$LOG_DIR/dev_up.pid"
mkdir -p "$LOG_DIR"

# Do not start a duplicate stack when a Codespace reconnects.
if curl -fsS http://127.0.0.1:5173/ >/dev/null 2>&1 \
  && curl -fsS http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
  echo "Content Orchestrator test stack is already running."
  exit 0
fi

# A stale background process can survive a terminal reconnect; stop only the
# process that this wrapper previously created, never arbitrary user processes.
if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
    kill "$old_pid" 2>/dev/null || true
  fi
fi

nohup bash scripts/dev_up.sh --simulation >"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"

for _ in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:5173/ >/dev/null 2>&1 \
    && curl -fsS http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
    echo "Content Orchestrator simulation is ready on forwarded port 5173."
    exit 0
  fi
  if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Content Orchestrator test stack exited before becoming ready." >&2
    tail -n 120 "$LOG_FILE" >&2 || true
    exit 1
  fi
  sleep 2
done

echo "Timed out waiting for Content Orchestrator test stack." >&2
tail -n 120 "$LOG_FILE" >&2 || true
exit 1
