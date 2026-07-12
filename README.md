# Editorial

Editorial is a fiction-focused desktop editor built for drafting and revision. it makes no use of AI, LLM, or similar systems. It uses only algorithmic detection to highlight writing patterns, allowing an editor to quickly correct a manuscript of 100,000 words or more. it does not make changes on its own, instead just highlighting possible issues so a skilled edior can work.

## Downloads
- Installer (recommended): https://github.com/FoolishFrost/Editorial/releases/download/v1.3.17/Editorial-Setup-1.3.17.exe
- Portable ZIP: https://github.com/FoolishFrost/Editorial/releases/download/v1.3.17/Editorial-1.3.17-portable.zip
- Release notes: https://github.com/FoolishFrost/Editorial/releases/tag/v1.3.17

## Documentation
- User manual (Wiki): https://github.com/FoolishFrost/Editorial/wiki

## Features
Editorial keeps the writing experience focused on fiction work while letting you run targeted analysis modes against the current draft:
- **Filter Words**: Highlights generic filter verbs (saw, heard, noticed) to bring the reader closer to the character's direct experience. Supports POV-aware character filtering.
- **Weak Modifiers**: Highlights weak adverbs and modifiers (very, suddenly, basically) to encourage stronger verb selections.
- **Punctuation**: Flags dialogue formatting anomalies (misplaced quotes, spaced dashes, loud double-punctuation, ellipsis irregularities). Includes options to format ellipses to standard unspaced formatting (`...`).
- **Dialogue Tags**: Highlights suspect dialogue tag patterns and related punctuation/tag combinations.
- **Emotion Catcher**: Highlights abstract emotional keywords (angry, sad, terrified) to identify show-don't-tell opportunities.
- **Proximity Echo Radar**: Detects nearby word repetitions within a configurable sliding scale window (1-100 words distance, default 80).
- **Rhythm & Pacing**: Heatmap-style sentence-length analyzer showing Short, Balanced, and Long sentences based on a user-adjustable max threshold slider (5-50 words, default 19).
- **Sentence Architecture**: Analyzes the structural blueprint of your prose, targeting 5 specific structural patterns (Subject-First Opener, Participial Launch, Contextual Lead, Echoing Hinge, Simultaneous Setup) and Fragments. Uses a weighted, non-washout line heatmap to highlight structural variety. Includes an option to ignore dialogue text.
- **N-gram Scan**: Analyzes overused word combination frequencies (Single Words, Word Pairs, Word Triples). Clicking any phrase highlights all matches progressively, showing progress in the status bar, and displaying occurrence ticks instantly in the left-side line heatmap gutter for quick scroll navigation.
- **Cliches**: Scans text against standard or customizable cliché databases (`cliches.txt`).
- **Redundancies**: Highlights duplicate or redundant wording patterns based on customized rules (`redundancies.txt`).
- **Passive Voice**: Locates passive construction patterns (was eaten, had been seen).
- **Spell Checking**: Highlights spelling errors with background red squiggles. Supports inline spelling suggestions, ignoring words, and custom user dictionaries (`dictionary.json`). Fully supports both straight (`'`) and curly (`’`) apostrophes in contractions.

## Source
- Repository: https://github.com/FoolishFrost/Editorial
