#!/usr/bin/env bash

set -euo pipefail

# mydba-tui macOS build script
#
# Creates a distributable macOS package bundle for local installation
# and development environments.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
DIST_DIR="${PROJECT_ROOT}/dist"
PACKAGE_DIR="${BUILD_DIR}/mydba-macos"

PYTHON_BIN="${PYTHON_BIN:-python3}"


echo "Building mydba-tui macOS package..."

cd "${PROJECT_ROOT}"


if [[ ! -d ".venv" ]]; then
    echo "Creating build virtual environment..."

    "${PYTHON_BIN}" -m venv .venv
fi


source .venv/bin/activate


echo "Installing build dependencies..."

python -m pip install --upgrade pip
python -m pip install build wheel


echo "Cleaning previous build artifacts..."

rm -rf "${BUILD_DIR}"
rm -rf "${DIST_DIR}"

mkdir -p "${PACKAGE_DIR}"


echo "Building Python package..."

python -m build


echo "Collecting installation files..."

mkdir -p "${PACKAGE_DIR}/packages"

cp -r "${DIST_DIR}"/* "${PACKAGE_DIR}/packages/"


echo "Copying macOS resources..."

if [[ -d "packaging/macos/resources" ]]; then
    cp -r packaging/macos/resources/* "${PACKAGE_DIR}/"
fi


echo "Creating dependency bundle..."

python -m pip freeze > "${PACKAGE_DIR}/requirements.txt"


echo "Creating archive..."

tar -czf \
    "${DIST_DIR}/mydba-macos-bundle.tar.gz" \
    -C "${BUILD_DIR}" \
    "$(basename "${PACKAGE_DIR}")"


echo ""
echo "macOS package created:"
echo "  ${DIST_DIR}/mydba-macos-bundle.tar.gz"
