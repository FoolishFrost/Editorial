Editorial v1.2.4
================

Simple Change Notes
-------------------
- Added **Sentence Architecture** mode to target prose repetition patterns.
- Implemented **Syntax Stacks** monitoring (3+ consecutive identical patterns in a 100-word moving window).
- Re-styled stacked variants with intensified highlighting and solid outline borders.
- Updated density heatmap to display stacked segments in brighter colors.
- Removed "Ignore Dialogue" from the Tools menu while keeping it as a context-aware toolbar checkbox toggle.
- Refactored architecture classifier to operate on the sentence level to prevent odd partial highlights.
- Optimized syntax stack detection to run in $O(N)$ time, avoiding hangs on full-length novels.

User-Facing Changes
-------------------
- Writers can now analyze their prose structure and spot repetitive grammatical patterns (Subject-First Opener, Participial Launch, Contextual Lead, Echoing Hinge, Simultaneous Setup) instantly.
- Repeated ruts (Syntax Stacks) are highlighted with a distinct solid border outline and represented as bright bands on the right-hand density sidebar.
- Added toolbar checkbox to easily ignore/ignore dialogue when checking prose structure.

Fixes
-----
- Refactored sentence architecture scanning to analyze at the sentence level instead of syntactic clause subtrees, preventing partial sentence highlights.
- Optimized syntax stack analysis algorithm to exit early when word window size limits are exceeded, making novel processing lightning-fast.
