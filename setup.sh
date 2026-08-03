#!/usr/bin/env bash
# setup.sh — Unitary Reasoner dev environment (git-bash / WSL)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== Unitary Reasoner — setup ==="

# 1. Python version check
PYTHON="${PYTHON:-python}"
PY_VER=$("$PYTHON" --version 2>&1 | grep -oP '\d+\.\d+')
echo "Python: $("$PYTHON" --version)  (need 3.10+)"

# 2. Create venv
if [ ! -d .venv ]; then
    echo "Creating .venv..."
    "$PYTHON" -m venv .venv
fi
source .venv/bin/activate

# 3. Install deps
echo "Installing dependencies..."
pip install -q -e ".[dev]"

# 4. Verify Ollama
echo "Checking Ollama..."
if command -v ollama &>/dev/null; then
    echo "Ollama: $(ollama --version)"
    if ollama list 2>/dev/null | grep -q gemma4; then
        echo "Gemma 4EB: available"
    else
        echo "WARNING: gemma4:e4b not pulled — run: ollama pull gemma4:e4b"
    fi
else
    echo "WARNING: ollama not found — install from https://ollama.com"
fi

# 5. Verify
echo "Running tests..."
python -m pytest -q

echo ""
echo "=== Setup complete ==="
echo "Activate: source .venv/bin/activate"
echo "Run demo: python demo.py"