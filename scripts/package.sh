#!/usr/bin/env bash

set -euo pipefail

# mydba-tui packaging helper
#
# Creates release packages for supported platforms.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PLATFORM="${1:-}"


usage() {
    echo "Usage:"
    echo "  $0 linux"
    echo "  $0 macos"
    echo ""
    echo "Examples:"
    echo "  ./scripts/package.sh linux"
    echo "  ./scripts/package.sh macos"
}


if [[ -z "${PLATFORM}" ]]; then
    usage
    exit 1
fi


cd "${PROJECT_ROOT}"


case "${PLATFORM}" in

    linux)
        echo "Packaging Linux distribution..."
        ./scripts/build_linux.sh
        ;;

    macos)
        echo "Packaging macOS distribution..."
        ./scripts/build_macos.sh
        ;;

    *)
        echo "Unsupported platform: ${PLATFORM}"
        usage
        exit 1
        ;;

esac


echo ""
echo "Packaging completed successfully."
