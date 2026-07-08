Editorial v1.2.9
================

Simple Change Notes
-------------------
- Refined dialogue ignoring logic inside the Sentence Architecture tool: when "Ignore Dialogue" is active, highlight tag ranges are automatically trimmed to **exclude** any leading or trailing quoted speech.
- This ensures dialogue-only clauses are completely unhighlighted, and mixed sentences (e.g. Dialogue + Narrative) highlight only the narrative parts.

User-Facing Changes
-------------------
- No more dialogue highlights will appear when "Ignore Dialogue" is checked, even if the dialogue is part of a larger tagged sentence. Only narrative blocks are highlighted.
