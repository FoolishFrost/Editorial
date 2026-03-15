Editorial Build And Release Rules
=================================

Use this file as the source of truth for build/release workflow.
If asked to "build as per BUILD.md", follow these steps exactly.

Versioning
----------
- Use semantic versioning: MAJOR.MINOR.PATCH.
- For user-visible features, bump MINOR (example: 1.0.0 -> 1.1.0).
- For bug fixes only, bump PATCH (example: 1.1.0 -> 1.1.1).
- Update versions in these files before packaging:
  - editorial.py -> APP_VERSION
  - scripts/package.ps1 -> default -Version parameter
  - installer/Editorial.iss -> MyAppVersion (handled automatically by package.ps1 when -Version is passed)

Git And Tags
------------
- Commit release changes with a message like: release: vX.Y.Z
- Create a matching annotated tag: vX.Y.Z
- Push commit and tags:
  - git push
  - git push --tags
- About dialog should show APP_VERSION and, when available, current git commit/tag.

Build Steps (Windows)
---------------------
1. Activate environment:
   - & .\.venv\Scripts\Activate.ps1
2. Run packaging script:
   - .\scripts\package.ps1 -Version X.Y.Z
3. Verify outputs:
   - dist/Editorial.exe
   - release/Editorial-Setup-X.Y.Z.exe (if Inno Setup is installed)

GitHub Release
--------------
- Create or update a GitHub release for tag vX.Y.Z.
- Upload binaries produced by the build step:
  - Installer EXE
  - Portable EXE/ZIP if produced
- Keep release title/tag aligned with APP_VERSION.

Update Checker Contract
-----------------------
- The in-app "Check for Updates" uses GitHub latest release API.
- It compares latest tag version with APP_VERSION.
- It should list release assets so users can open binary download links.
