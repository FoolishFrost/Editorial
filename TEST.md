Editorial Local Test Checklist
==============================

Purpose
-------
Use this checklist after build and before publish.
Run through each section and mark pass/fail.

Build Under Test
----------------
- App version: 1.1.0
- Executable: dist/Editorial.exe
- Installer: release/Editorial-Setup-1.1.0.exe

Stage 2: Manual Validation
--------------------------

1. Launch And Stability
- Launch from dist/Editorial.exe.
- Launch from installed build (optional).
- Confirm no startup crash.
- Confirm main window renders correctly.

2. Core Editor Flows
- New, Open, Save, Save As.
- Undo/Redo and clipboard actions.
- Find/Replace and Replace All.
- Word count dialog.

3. Filter Analyzer Flows
- Toggle Filter Words on/off.
- Run update after edits.
- Confirm highlight rendering and no UI freeze.
- Confirm POV selector affects results.

4. New Help Menu Features
- Help -> Docs opens GitHub wiki.
- Help -> Check for Updates opens progress popup.
- Confirm release data appears (tag/title/date).
- Confirm binary asset Open buttons work.

5. About Dialog And Versioning
- Help -> About Editorial shows version 1.1.0.
- If run from git working tree, confirm commit/tag lines appear when available.

6. Packaging Sanity
- Confirm dist/Editorial.exe exists and runs.
- Confirm release/Editorial-Setup-1.1.0.exe exists.
- Confirm installer wizard completes and app launches.

7. Regression Spot Check
- Verify line numbers and zoom behavior.
- Verify n-gram scan still works.
- Verify export highlighted RTF and tagged text still work.

Exit Criteria
-------------
- All critical paths pass.
- No blockers remain for release.
- Any non-blocking issues are documented before publish.

Stage 3 Trigger
---------------
When all checks pass, run publish using:
- "run publish.md"
