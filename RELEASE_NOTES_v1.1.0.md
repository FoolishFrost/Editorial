Editorial v1.1.0
================

Simple Change Notes
-------------------
- Added a Docs menu item that opens the Editorial wiki.
- Added Check for Updates to fetch latest GitHub release info in-app.
- Update popup now lists release binaries with quick open links.
- About dialog now shows app version plus git commit/tag when available.
- Improved analyzer and n-gram performance for smoother large-file use.
- Installer now carries richer publisher/contact metadata for a clearer install experience.
- Wiki now includes SmartScreen and browser download-unblock steps (Chrome/Edge).

User-Facing Changes
-------------------
- New Help menu shortcuts:
  - Docs -> opens the GitHub Wiki
  - Check for Updates -> checks latest release and binary assets
- Export actions reuse cached analysis data when possible.
- Installer/version workflow is now more consistent across app + packaging.

Fixes
-----
- Fixed installer version propagation in packaging script so requested version is applied reliably.
- Packaging script now supports same-version rebuilds without failing when version already matches.

Known Limitations
-----------------
- Update checker expects internet access and GitHub API availability.
- Portable ZIP for v1.1.0 must be uploaded alongside installer for README links to both assets.
