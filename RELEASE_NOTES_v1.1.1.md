Editorial v1.1.1
================

Simple Change Notes
-------------------
- Reduced editor jank during highlight passes, especially in larger documents.
- Fixed a packaging issue that could cause missing local modules in the built EXE.
- Export options are now mode-aware: exports are disabled when no analysis mode is active.
- Rhythm & Pacing keeps rich-color RTF export, while Tagged Text export is intentionally disabled.
- Improved sentence pacing detection for ellipsis-at-line-end cases.
- Reduced false positives in dialogue tag detection across paragraph boundaries.
- Build workflow now generates a portable ZIP artifact for releases.

User-Facing Changes
-------------------
- Analysis highlighting applies more smoothly while scrolling.
- Export menu behavior now matches active mode semantics.
- Rhythm & Pacing output remains available through highlighted RTF export.

Fixes
-----
- Repaired punctuation-mode processing stall observed near 55% in affected runs.
- Corrected dialogue-tag regex behavior that could match across newlines.
- Added explicit hidden imports in PyInstaller specs to improve bundled runtime reliability.

Known Limitations
-----------------
- Update checker requires internet access and GitHub API availability.
- Windows SmartScreen publisher verification still depends on Authenticode signing.
