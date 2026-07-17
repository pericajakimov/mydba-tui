#!/usr/bin/env bash

set -euo pipefail

# mydba-tui lint script
#
# Runs static code quality checks.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${PROJECT_ROOT}"


if [[ -d ".venv" ]]; then
    source .venv/bin/activate
fi


echo "Running Ruff lint checks..."

ruff check .


echo ""
echo "Lint checks completed successfully."
