#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting VeritasAI Backend..."
if [ ! -f /.requirements_installed ]; then
	echo "Installing Python requirements..."
	python3 -m pip install -r requirements.txt || true
	touch /.requirements_installed
fi

echo "Waiting for Ollama (if enabled)..."
python3 wait_for_ollama.py || true

exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-1}"
