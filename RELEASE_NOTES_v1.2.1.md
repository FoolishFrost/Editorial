Editorial v1.2.1
================

Simple Change Notes
-------------------
- Added Proximity Echo Radar sensitivity slider (range 1-100, default 80) to dynamically adjust word distance checks.
- Added Rhythm & Pacing length slider (range 5-50, default 19) to set maximum long sentence length and automatically calculate relative short (20%) and average (60%) thresholds.
- Fixed spelling checker to support curly single quotes and apostrophes, preventing words like `didn’t` or `hadn’t` from being incorrectly flagged as typos.
- Changed "Convert Ellipses to Spaced" to "Convert Ellipses to Standard", replacing all ellipsis styles with unspaced three-dots `...` instead of spaced `. . .`.
- Fixed pacing analysis highlighting spill where highlight colors stretched across the empty right margin of the editor.
- Bundled external configuration files `cliches.txt` and `redundancies.txt` in both standalone ZIP and installer builds.
- Refactored toolbar packing order to place sliders to the left of the dynamic Refresh button, preventing widget grab and hover glitches when buttons appear.

User-Facing Changes
-------------------
- Dynamic range controls for Echo Radar and Rhythm & Pacing allow real-time tuning of review parameters directly in the mode toolbars.
- Punctuation format options clean up ellipses to standard unspaced formatting (`...`).
- Typo highlights no longer flag common contractions when formatted with curly apostrophes (`’`).
- Highlights in Rhythm & Pacing end cleanly at line breaks without filling background empty space.

Fixes
-----
- Corrected pacing block segmentation to split on single newlines (`\n`) so analysis boundaries do not cross paragraphs.
- Expanded ellipsis terminal splitting in pacing analyzer to treat unicode ellipsis `…` as a sentence end if followed by capitalized text, line breaks, or block boundaries.
- Corrected spellcheck tokenization regex to support curly apostrophes and normalize them before contraction checks.
- Fixed layout shifts in mode bars by anchoring the dynamic Refresh button to the right of active controls.

Known Limitations
-----------------
- Changes to Echo Radar or Rhythm & Pacing sliders display a "Refresh" indicator to manually trigger a re-scan.
- Windows SmartScreen publisher warning will remain present unless the built binary is signed.
