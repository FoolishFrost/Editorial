# Release Notes v1.3.14

## Overview
This release introduces a major refactoring of the Editorial codebase, splitting the main application monolith into cleaner, specialized modules. It also implements critical performance optimizations to resolve typing lag and spellchecking overhead.

## Simple Change Notes
* **Modularized Subsystems**: Extracted spelling, find/replace, text formatting, and n-gram counting into clean, dedicated modules (`spellcheck_subsystem.py`, `formatting_subsystem.py`, `ngram_subsystem.py`, `search_subsystem.py`).
* **Clean Mode Scripts**: Extracted all 11 editing analysis modes (Echo Radar, Pacing, Cliches, etc.) into separate, lightweight scripts.
* **Typing Lag Fixed**: Optimized cursor movement and arrow-key navigation to skip heavy, layout-blocking word-count scans and indent updates.
* **Faster Spellcheck**: pySpellChecker scans are now optimized to process unique words only, filtering them through session ignores first.
* **Performance Boost**: Execution speed of the automated test suite improved by **2.4x** (reduced from 10.43s to 4.41s).
* **Fully Backwards Compatible**: Facade layers ensure CLI runners and testing frameworks work seamlessly without modifications.
