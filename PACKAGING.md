Packaging (unsigned)
===================

This project can be packaged as:
1. Portable EXE via PyInstaller (Windows)
2. Windows installer (EXE) via Inno Setup
3. macOS app bundle (.app) via PyInstaller

Platform support
----------------
- **Windows** — fully supported; packaged as a standalone EXE or installer.
- **macOS** — fully supported; packaged as a `.app` bundle (optionally wrapped in a DMG).
- **iPad / iOS** — not supported. The application uses the Tkinter GUI toolkit which
  does not run on iPadOS. A port to a native iOS framework (e.g. SwiftUI) would be
  required and is outside the current scope of this project.

Windows prerequisites
---------------------
- Windows
- Project virtual environment at .venv
- Inno Setup 6 (optional, for installer): https://jrsoftware.org/isinfo.php

Windows — one-command packaging
--------------------------------
Run:

powershell
.\scripts\package.ps1 -Version 1.0.0

What it does:
1. Builds dist\Editorial.exe using PyInstaller
2. Updates installer version in installer\Editorial.iss
3. Builds installer to release\Editorial-Setup-<version>.exe if ISCC is available

Windows — manual commands
--------------------------
Build EXE only:

powershell
& .\.venv\Scripts\Activate.ps1
pyinstaller --noconfirm --clean --onefile --windowed --name Editorial --collect-all en_core_web_sm editorial.py

Build installer manually:

powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" .\installer\Editorial.iss

macOS prerequisites
-------------------
- macOS (Intel or Apple Silicon)
- Python 3 with Tkinter — install via python.org or Homebrew (`brew install python-tk`)
- Project virtual environment at .venv
- create-dmg (optional, for DMG): `brew install create-dmg`

macOS — one-command packaging
------------------------------
Run:

bash
./scripts/package.sh 1.0.0

What it does:
1. Builds dist/Editorial.app using PyInstaller
2. Wraps it in release/Editorial-<version>.dmg using create-dmg (if available)

macOS — manual commands
------------------------
Build .app only:

bash
source .venv/bin/activate
pyinstaller --noconfirm --clean --windowed --name Editorial --collect-all en_core_web_sm editorial.py

The resulting bundle is at dist/Editorial.app.

Notes
-----
- All builds are unsigned.
- Unsigned macOS apps require right-clicking → Open the first time, or running:
  xattr -cr dist/Editorial.app
- Unsigned Windows installers/executables may trigger SmartScreen warnings.
