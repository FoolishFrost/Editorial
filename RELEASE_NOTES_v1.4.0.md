# Release Notes v1.4.0

## Overview
This release elevates the spelling checker to a first-class editor mode with its own dedicated visual density heatmap (density band) in the sidebar. This aligns the proofreading workflow with Editorial's twelve other professional prose analysis passes.

## Key Changes
* **Dedicated Spelling Mode**: Added "Spelling Checker" as an active editor mode. Underlines representing misspelled words are now focused and displayed only when this mode is selected.
* **Typo Density Heatmap**: Generated a dedicated red density band in the sidebar when in Spelling Checker mode. Writers can easily identify clusters of typos and click sections of the density band to jump directly to those parts of the document.
* **UI Streamlining**: Removed the legacy global checkbutton from the Tools menu and the "Spelling Checker Enabled" checkbox from the settings panel, eliminating distraction and visual clutter during active drafting.
* **Automated Test Validation**: Updated the integration test suite to verify mode-based spelling checker transitions.
