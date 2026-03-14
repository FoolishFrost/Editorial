#!/usr/bin/env bash
# package.sh — Build Editorial.app for macOS (unsigned)
set -euo pipefail

VERSION="${1:-1.0.0}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

VENV_ACTIVATE="$REPO_DIR/.venv/bin/activate"
if [[ ! -f "$VENV_ACTIVATE" ]]; then
    echo "Error: virtual environment not found at $REPO_DIR/.venv" >&2
    echo "Create one with: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
fi

echo "[1/2] Building Editorial.app with PyInstaller..."
# shellcheck disable=SC1090
source "$VENV_ACTIVATE"
pyinstaller --noconfirm --clean --windowed --name Editorial \
    --collect-all en_core_web_sm editorial.py

echo "[2/2] Packaging into DMG (requires create-dmg)..."
if command -v create-dmg &>/dev/null; then
    mkdir -p release
    create-dmg \
        --volname "Editorial $VERSION" \
        --window-size 540 380 \
        --icon-size 128 \
        --icon "Editorial.app" 130 160 \
        --app-drop-link 410 160 \
        "release/Editorial-$VERSION.dmg" \
        "dist/Editorial.app"
    echo "DMG written to release/Editorial-$VERSION.dmg"
else
    echo "create-dmg not found — skipping DMG creation."
    echo "Install it with: brew install create-dmg"
    echo "The .app bundle is at dist/Editorial.app"
fi

echo "Done."
