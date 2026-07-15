# Release Notes v1.5.0

## New Feature — Unified Mode Lists Management

Replaced the separate **POV Settings** and **Mode Ignores** tabs in the Settings panel with a consolidated, fully-featured **Mode Lists** tab.

**Features:**
* **Dropdown Selection**: A single combobox to switch between and edit the following customizable lists:
  * `POV Names` (active character names for the Sensory Filter Words mode)
  * `Filter Words` (sensory lemmas like *see*, *look*, *hear*)
  * `Cliches` (patterns from the cliché scanner database)
  * `Redundancies` (semantic redundancy check combinations)
  * `Emotion Catcher` (internal-state tell-not-show emotional terms)
* **Full List Control**: You can add new terms (with duplicate validation) and remove selected items from any list directly in the Settings window. Changes are dynamically persisted to their respective configuration text files or configuration settings.
* **Reset to Defaults**: Added a confirmation-guarded **Reset to Defaults** button that allows you to easily restore the selected list back to its original factory defaults.
* **Consolidated Pronoun Configuration**: Moved the POV Pronoun Filter Settings combobox to the **Mode Settings** tab alongside pacing and repetition focus ranges.

---

## Spell Checker & Contraction Improvements

We redesigned spelling tokenization and validation for contractions to eliminate partial highlights and catch negative contractions typos.

* **Whole-Word Highlighting**: Spelling errors on contractions (e.g. `did'nt`) are now highlighted as a single full word, rather than parsing and highlighting only the suffix or stem fragment.
* **Contraction Typos**: The negative contraction suffix `'t` is now strictly restricted to whitelisted negation stems (e.g., `didn't`, `wasn't`). Typos like `done't` are caught and flagged.
* **Standard Contractions & Possessives**: Normal contractions (like `I'm`, `didn't`) and valid possessive stems/POV names (like `Kindra's`, `writer's`) are correctly whitelisted and ignore-checked.

---

## Context Menu Refinements for Word Confusions

* Right-clicking word confusion rules with multiple options (such as `lie / lay (past of lie)`) now displays them as **separate, distinct suggestions** in the context menu (e.g., *"Change to 'lie'"* and *"Change to 'lay (past of lie)'"*).
* Clicking a choice cleanly inserts the selected word with explanation notes and parentheticals stripped automatically from the final inserted text.
