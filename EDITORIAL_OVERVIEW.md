# Editorial: Fiction-Focused Prose Editor

Editorial is a lightweight, offline-first desktop editor designed specifically for fiction writers. Unlike traditional word processors (such as Microsoft Word) or generic code editors, Editorial blends a focused drafting environment with twelve customized prose analysis passes to help writers spot mechanical errors, stylistic ruts, and cadential monotony.

---

## Core Philosophy

1. **Local and Private**: All text processing, spellchecking, and language analysis run entirely on the local machine. Drafts are never sent to external servers or third-party APIs.
2. **Distraction-Free Focus**: The user interface is clean, dark-themed, and uncluttered. It keeps the text front and center.
3. **No Keystroke Lag**: Analysis highlights do not refresh on every keystroke. The editor marks highlights as "stale" when edits occur, allowing writers to work smoothly and click **Refresh** when they are ready to run the analyzers.
4. **Layout Continuity**: Formatting tools (such as Smart Quotes conversion or Whitespace Cleaning) automatically preserve the user's screen scroll position and cursor coordinates, preventing layout jumping.

---

## Standard Features

* **Drafting Layout**: Includes paragraph-level first-line indent toggling (simulating a print book layout) and line numbering.
* **Smart Punctuation Utilities**: Automated conversion between smart (curly) and straight quotes, spaced and unspaced ellipses, and clean whitespace operations.
* **Flexible Exports**:
  * **Highlighted RTF**: Compiles the draft with the active mode's color highlights preserved. The output opens directly in Word, Scrivener, or LibreOffice.
  * **Tagged Text**: Exports plain text with bracketed markdown-style tags around active issues (e.g. `[DTAG:said angrily]`) for further script processing.

---

## Detailed Breakdown of Analysis Modes

### 1. Filter Words
* **Goal**: Minimize narrative distance by catching sensory filters.
* **Mechanism**: Scans for verbs like *saw*, *heard*, *felt*, *thought*, *knew*, and *noticed*.
* **POV Integration**: Allows entering character names in the toolbar. It flags filters in Red if preceded by the current POV character's pronoun or name (e.g., *"He heard"*), and Purple for generic instances.
* **Why it matters**: Filters separate the reader from the character's immediate experience. (e.g., *"She felt the cold wind"* vs. *"The wind bit her cheeks"*).

### 2. Weak Modifiers
* **Goal**: Encourage stronger verbs by highlighting lazy adverbs and qualifiers.
* **Mechanism**: Highlights qualifiers (*very*, *really*, *slightly*, *suddenly*, *just*, *somewhat*) in Orange.
* **Why it matters**: Replacing a verb-adverb pair with a strong, active verb tightens the prose. (e.g., *"ran very fast"* vs. *"sprinted"*).

### 3. Punctuation
* **Goal**: Spot mechanical punctuation and speech grammar issues.
* **Mechanism**: Highlights unbalanced quotation marks, missing paragraph quotation bounds, double punctuation, and loud exclamation tags (*!!*, *!?*) in Red or Yellow.
* **Why it matters**: Catches formatting slips before manuscript submission.

### 4. Dialogue Tags
* **Goal**: Tidy dialogue attribution and dialogue flow.
* **Mechanism**: Flags speech tags appended with adverbs (e.g. *said angrily*) or action verbs incorrectly formatted as tags (e.g. *she smiled, "No"*).
* **Why it matters**: Let the spoken dialogue or physical beats carry the action. Attribution tags should remain functionally invisible.

### 5. Emotion Catcher
* **Goal**: Help writers transition from "telling" emotions to "showing" them.
* **Mechanism**: Highlights abstract emotion terms (*angry*, *scared*, *sad*, *terrified*, *grief*) in Red.
* **Why it matters**: Flags spots where a character's internal state is flatly named rather than demonstrated through physical actions, body language, or dialogue.

### 6. Proximity Echo Radar
* **Goal**: Prevent vocabulary repetition.
* **Mechanism**: Scans a moving word window (sensitivity adjustable from 1 to 100 words via a toolbar slider) for identical word stems. Echoes are highlighted in Blue.
* **Why it matters**: Accidental word echo (using *door* three times in a paragraph) breaks the reading rhythm.

### 7. Rhythm and Pacing
* **Goal**: Visualize the cadence of the prose.
* **Mechanism**: Renders an interactive sentence-length heatmap:
  * Cool blue tones represent short, punchy sentences.
  * Warm orange/red tones represent long, complex sentences.
* **Why it matters**: Varied sentence length creates a pleasant flow. Heatmaps quickly expose blocky bands of monotony—either excessive long-winded exposition (orange bands) or choppy, children's-book-style fragments (blue bands).

### 8. Sentence Architecture
* **Goal**: Identify and vary the grammatical structure of sentence openings.
* **Mechanism**: Uses a spaCy-powered parser to categorize every sentence into one of six structural archetypes:
  * **Subject-First Opener** (Steel Blue): Begins directly with the subject (e.g., *They walked home.*).
  * **Participial Launch** (Warm Gold): Begins with an `-ing` phrase (e.g., *Opening the door, she...*).
  * **Contextual Lead** (Soft Amethyst): Begins with a prepositional setting or temporal lead (e.g., *In the dark room, he...*).
  * **Echoing Hinge** (Terracotta): Symmetrical compounds (e.g., *The storm hit, and the lights died.*).
  * **Simultaneous Setup** (Sage Green): Begins with conjunctions like *As*, *When*, or *While*.
  * **Fragment** (Slate Grey): Incomplete grammatical clauses.
* **Why it matters**: Writers frequently fall into a comfortable rhythm (such as writing only subject-first sentences). Sentence Architecture makes these structural ruts visible.

### 9. Cliches
* **Goal**: Keep descriptive language original.
* **Mechanism**: Matches text against a customizable local clichés dictionary (`cliches.txt`). Matches highlight in Teal.
* **Why it matters**: Helps eliminate tired expressions (e.g., *cold as ice*, *at the end of the day*) in favor of unique descriptions.

### 10. Redundancies
* **Goal**: Tighten prose by removing duplicate meanings.
* **Mechanism**: Highlights common redundancies (e.g., *completely empty*, *final outcome*, *added bonus*) in Yellow based on `redundancies.txt`.
* **Why it matters**: Word count efficiency and stylistic tightness.

### 11. Passive Voice
* **Goal**: Keep narrative voice active.
* **Mechanism**: Flags passive helper verb combinations (e.g. *was thrown*, *were chosen*) in Pink.
* **Why it matters**: Direct action is usually more engaging than passive descriptions.

### 12. Spell Checking
* **Goal**: Inline typo spotting.
* **Mechanism**: Underlines spelling errors in real-time. Right-click suggestions provide five alternatives, along with options to ignore the word or save it to a persistent custom user dictionary (`custom_dictionary.json`).
