Editorial v1.2.5
================

Simple Change Notes
-------------------
- Added the **Fragment** sentence archetype (`arch_fragment`) to target incomplete thoughts, noun phrases, dropped-subject clauses, and elliptical fragments.
- Refined the **Subject-First Opener** complexity rules to target only simple structures and prevent false alerts on long sentences containing complex subordinate clauses (`advcl`/`ccomp` with their own subject/marker).
- Updated color mappings: mapped Sage Green to Simultaneous Setup, and Pale Grey to Fragments.
- Updated status bar legend key to display all 6 active keys.
- Expanded RTF export configurations to fully support all 6 normal and stacked archetypes.

User-Facing Changes
-------------------
- Writers can now analyze sentence structure for **Fragments** (e.g. *"Right."*, *"Or any, really."*, *"Sixes, extra limbs."*).
- Complex subject-first sentences (e.g. *"I rolled toward the sword, letting myself take in the camp as it flashed by my vision"* ) containing subordinate clauses are no longer flagged as drone-like structures, reducing highlight noise.

Fixes
-----
- Resolved the odd partial sentence highlight issues by shifting analysis entirely to the sentence level, ensuring clean, contiguous outlines.
