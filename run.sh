#!/usr/bin/env bash
# run.sh — Start the MIDAS Swing Strategy Test Bench
# Usage: ./run.sh [--port 7432] [--no-reload]

set -e

PORT=${PORT:-7432}
RELOAD="--reload"

for arg in "$@"; do
  case $arg in
    --port=*) PORT="${arg#*=}" ;;
    --no-reload) RELOAD="" ;;
  esac
done

# Activate venv if present
if [ -d ".venv" ]; then
  source .venv/bin/activate
elif [ -d "../.venv" ]; then
  source ../.venv/bin/activate
fi

echo ""
echo "  ███╗   ███╗██╗██████╗  █████╗ ███████╗"
echo "  ████╗ ████║██║██╔══██╗██╔══██╗██╔════╝"
echo "  ██╔████╔██║██║██║  ██║███████║███████╗"
echo "  ██║╚██╔╝██║██║██║  ██║██╔══██║╚════██║"
echo "  ██║ ╚═╝ ██║██║██████╔╝██║  ██║███████║"
echo "  ╚═╝     ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝╚══════╝"
echo ""
echo "  Swing Strategy Test Bench"
echo "  ──────────────────────────────────────"
echo "  → App:      http://localhost:${PORT}"
echo "  → API docs: http://localhost:${PORT}/docs"
echo ""
echo "  Qwen: make sure Ollama is running"
echo "  Install: ollama pull qwen2.5vl:32b"
echo "  ──────────────────────────────────────"
echo ""

uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --log-level info \
  $RELOAD
