#!/usr/bin/env bash

set -euo pipefail

# mydba-tui test script
#
# Runs the automated test suite.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${PROJECT_ROOT}"


if [[ -d ".venv" ]]; then
    source .venv/bin/activate
fi


echo "Running test suite..."

pytest


echo ""
echo "Tests completed successfully."
