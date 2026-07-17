#!/usr/bin/env bash

set -euo pipefail

# mydba-tui development runner
#
# Runs the application from the local source tree using the current
# development environment.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${PROJECT_ROOT}"

if [[ ! -d ".venv" ]]; then
    echo "Virtual environment not found: .venv"
    echo "Create it first with:"
    echo "  python3 -m venv .venv"
    exit 1
fi

source .venv/bin/activate

echo "Starting mydba-tui development instance..."

python -m mydba_tui
