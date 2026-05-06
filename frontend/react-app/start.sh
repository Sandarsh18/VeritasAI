#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

npm install --legacy-peer-deps
npm run dev -- --host 0.0.0.0 --port 5173
