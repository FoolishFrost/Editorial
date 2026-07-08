Editorial v1.3.0
================

Simple Change Notes
-------------------
- Refactored `editorial.py` by extracting static configurations, theme color schemes, and keyword lists into `editorial_config.py`.
- Moved document/RTF export compilers into `editorial_export.py`.
- Decoupled GUI layout controllers from data compilation, reducing raw codebase size of `editorial.py` by ~400 lines and improving architectural modularity.

User-Facing Changes
-------------------
- None (pure architectural cleanup and refactoring session).
