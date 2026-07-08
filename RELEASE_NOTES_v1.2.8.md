Editorial v1.2.8
================

Simple Change Notes
-------------------
- Fixed a bug where dialogue sentences (e.g. `"What?"` or `"Yes."`) were marked as Fragments (`arch_fragment`) even when the "Ignore Dialogue" option was checked.
- Space and formatting tokens are now correctly ignored by the Sentence Architecture parser.

User-Facing Changes
-------------------
- Dialogue-only sentences are now properly excluded from Sentence Architecture scans when "Ignore Dialogue" is active, avoiding incorrect highlighting alerts inside dialogue quotes.
