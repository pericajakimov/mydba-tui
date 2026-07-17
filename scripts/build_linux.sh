#!/usr/bin/env bash

set -euo pipefail

# mydba-tui Linux build script
#
# Creates a distributable Linux package bundle suitable for offline
# installation on DBA tooling servers.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
DIST_DIR="${PROJECT_ROOT}/dist"
PACKAGE_DIR="${BUILD_DIR}/mydba-linux"

PYTHON_BIN="${PYTHON_BIN:-python3}"


echo "Building mydba-tui Linux package..."

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


echo "Collecting offline installation files..."

mkdir -p "${PACKAGE_DIR}/packages"

cp -r "${DIST_DIR}"/* "${PACKAGE_DIR}/packages/"


echo "Copying installation resources..."

if [[ -d "packaging/linux/files" ]]; then
    cp -r packaging/linux/files/* "${PACKAGE_DIR}/"
fi


echo "Creating requirements bundle..."

python -m pip freeze > "${PACKAGE_DIR}/requirements.txt"


echo "Creating archive..."

tar -czf \
    "${DIST_DIR}/mydba-linux-bundle.tar.gz" \
    -C "${BUILD_DIR}" \
    "$(basename "${PACKAGE_DIR}")"


echo ""
echo "Linux package created:"
echo "  ${DIST_DIR}/mydba-linux-bundle.tar.gz"
