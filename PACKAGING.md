Packaging (unsigned)
===================

This project can be packaged as:
1. Portable EXE via PyInstaller
2. Windows installer (EXE) via Inno Setup

Prerequisites
-------------
- Windows
- Project virtual environment at .venv
- Inno Setup 6 (optional, for installer): https://jrsoftware.org/isinfo.php

One-command packaging
---------------------
Run:

powershell
.\scripts\package.ps1 -Version 1.0.0

What it does:
1. Builds dist\Editorial.exe using PyInstaller
2. Updates installer version in installer\Editorial.iss
3. Builds installer to release\Editorial-Setup-<version>.exe if ISCC is available

Manual commands
---------------
Build EXE only:

powershell
& .\.venv\Scripts\Activate.ps1
pyinstaller --noconfirm --clean --onefile --windowed --name Editorial --collect-all en_core_web_sm editorial.py

Build installer manually:

powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" .\installer\Editorial.iss

Notes
-----
- This packaging is unsigned.
- Unsigned installers/executables may trigger SmartScreen warnings.
