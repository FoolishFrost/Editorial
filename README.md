# Editorial

Editorial is a fiction-focused desktop editor built for drafting and revision.

## Downloads
- Installer (recommended): https://github.com/FoolishFrost/Editorial/releases/download/v1.2.6/Editorial-Setup-1.2.6.exe
- Portable ZIP: https://github.com/FoolishFrost/Editorial/releases/download/v1.2.6/Editorial-1.2.6-portable.zip
- Release notes: https://github.com/FoolishFrost/Editorial/releases/tag/v1.2.6

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
- **Sentence Architecture**: Analyzes the structural blueprint of your prose, targeting 6 specific structural patterns (Subject-First Opener, Participial Launch, Contextual Lead, Echoing Hinge, Simultaneous Setup, and Fragment) and alerting you to **Syntax Stacks** (3+ repetitions in a 100-word window) to vary sentence structures for more interesting reading. Includes an option to ignore dialogue text.
- **Cliches**: Scans text against standard or customizable cliché databases (`cliches.txt`).
- **Redundancies**: Highlights duplicate or redundant wording patterns based on customized rules (`redundancies.txt`).
- **Passive Voice**: Locates passive construction patterns (was eaten, had been seen).
- **Spell Checking**: Highlights spelling errors with background red squiggles. Supports inline spelling suggestions, ignoring words, and custom user dictionaries (`dictionary.json`). Fully supports both straight (`'`) and curly (`’`) apostrophes in contractions.

## Source
- Repository: https://github.com/FoolishFrost/Editorial
