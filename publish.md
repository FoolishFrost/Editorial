Editorial Publish Runbook
=========================

Purpose
-------
Use this document to publish a new Editorial release and fully synchronize all public-facing project surfaces.
This file is intentionally procedural and should be executed step-by-step.

When To Run
-----------
- After build artifacts are created and validated (see BUILD.md).
- When code/docs changes are ready for public release.

Watch Files (Publish-Critical)
------------------------------
- README.md
  - Must point to current release tag and asset URLs.
- RELEASE_NOTES_vX.Y.Z.md
  - Must include Simple Change Notes (plain language bullets).
- publish.md
  - Keep this runbook current after each release.
- BUILD.md
  - Ensure build verification rules still match actual process.
- .gitignore
  - release/ should remain ignored unless intentionally tracking binaries.
- installer/Editorial.iss
  - Installer metadata should mirror About branding details where practical.

Preflight Checklist
-------------------
- Confirm app version is finalized and consistent:
  - editorial.py -> APP_VERSION
  - scripts/package.ps1 -> default Version
  - installer/Editorial.iss -> MyAppVersion
- Confirm local build artifacts exist and launch:
  - dist/Editorial.exe
  - release/Editorial-Setup-X.Y.Z.exe
  - Portable package if applicable
- Confirm release notes/changelog text is prepared.
- Prepare simple change notes for this release (3-7 short bullets, plain language).
- Confirm wiki/manual updates are drafted.

Step 1: Review Local Changes
----------------------------
- Review git status and diff.
- Decide whether each modified file belongs in this release.
- Remove accidental binaries/temp files from commit scope.

Step 2: Commit And Push Code Changes
------------------------------------
- If there are uncommitted release changes, commit them.
- Use a clear release commit message, e.g.:
  - release: vX.Y.Z
- Push branch to GitHub.
- Create and push annotated tag:
  - vX.Y.Z
- Keep release artifacts out of commit scope unless explicitly intended.

Acceptance criteria:
- GitHub branch shows latest commit.
- Release tag vX.Y.Z exists on remote.

Step 3: Publish GitHub Release
------------------------------
- Create or edit the GitHub release for tag vX.Y.Z.
- Title should match release version.
- Include release notes with:
  - Simple change notes (short bullets, non-technical wording first)
  - User-facing changes
  - Fixes
  - Known limitations
- Upload artifacts:
  - Installer EXE
  - Portable EXE/ZIP as applicable
- If using GitHub CLI:
  - Use release field name "name" when querying JSON output.
  - Do not use "title" as a JSON field in gh release view.

Acceptance criteria:
- Release page is live.
- Download links work.
- Asset filenames reflect version.
- Simple change notes are present and readable by non-technical users.
- Release includes both expected assets when available:
  - Editorial-Setup-X.Y.Z.exe
  - Editorial-X.Y.Z-portable.zip

Step 4: Update Wiki Manual
--------------------------
- Update user manual pages in the GitHub Wiki.
- Ensure any new features/menu items are documented with screenshots where useful.
- Verify install/update instructions match current release assets.
- Ensure troubleshooting includes current guidance for:
  - Windows SmartScreen prompts
  - Chrome/Edge blocked-download override flow
- If pushing via a cloned wiki repo, ensure git identity is configured in that repo before commit:
  - user.name
  - user.email

Minimum wiki pages to review each release:
- Home / Overview
- Installation / Upgrading
- Feature reference
- Troubleshooting (if new known issues)

Acceptance criteria:
- Wiki reflects current UI and workflow.
- No references to removed/renamed features.

Step 5: Update README
---------------------
- Update download links to current release assets.
- Update version references.
- Update release notes link/tag.
- Ensure docs/manual link points to current wiki.
- Verify feature list reflects shipped behavior.

Acceptance criteria:
- README install/download paths are valid.
- README matches current release and wiki.

Step 6: Final Public-Facing Audit
---------------------------------
Check these surfaces end-to-end:
- Repository landing page
- Latest GitHub release page
- README download links
- Wiki manual pages
- In-app update checker behavior (tag/version + asset listing)
- Verify repository default branch shows the release commit.
- Verify release tag resolves to the intended commit.
- Verify installer metadata matches intended branding (publisher/contact/update URL).
- Verify public docs do not imply unsigned builds will show verified publisher identity.

Release is complete only when all checks pass.

Post-Publish Cleanup
--------------------
- Optionally remove old local release artifacts that are superseded.
- Log any follow-up tasks discovered during publish audit.
- Remove temporary wiki clone folders created during publish automation.

Quick Operator Prompt
---------------------
If you ask an assistant to publish, use:
- "Publish as per publish.md"

Related
-------
- BUILD.md: Build and packaging rules
- PACKAGING.md: Packaging notes and prerequisites
