# Release Notes v1.4.8

## New Feature — Word Confusion Detection

The Spelling Checker now detects common homophones and frequently confused word pairs, flagging them with explanations and suggested corrections.

**Detected pairs:**
* **their / there / they're** — Flags possessive *their* used where existential *there* is needed, and vice versa. Also catches *they're* used as a possessive.
* **its / it's** — Flags *its* before a verb or auxiliary (where a contraction is likely intended), and *it's* before possessive nouns.
* **your / you're** — Flags *your* immediately before a verb, where *you're* is likely the intent.
* **then / than** — Flags *then* after a comparative adjective or adverb (e.g. *"better then"* → *"better than"*).
* **loose / lose** — Flags *loose* when used as a verb (e.g. *"don't loose it"*).
* **passed / past** — Flags *passed* after a motion verb used as a direction preposition (e.g. *"walked passed me"*).

Detection uses two complementary layers: fast regex rules for unambiguous patterns, and spaCy part-of-speech analysis for context-sensitive cases. Right-clicking a flagged confusion offers the suggested correction and an option to ignore it for the session.
